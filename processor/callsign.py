"""
Callsign extraction module for ATC communications.

Extracts airline callsigns (e.g., "Shamrock 603", "Ryanair 5N", "United 980")
while filtering out false positives like taxiways, runways, and flight levels.

Callsigns are always two parts: airline name + flight identifier.
"""

import re
from dataclasses import dataclass
from typing import Optional, List
from processor.cache import get_cache


@dataclass
class CallsignMatch:
    """Represents an extracted callsign with metadata."""
    callsign: str
    operator: Optional[str]
    icao: Optional[str]
    confidence: float
    start_pos: int
    end_pos: int


# NATO phonetic alphabet mapping
PHONETIC_ALPHABET = {
    'ALPHA': 'A', 'ALFA': 'A',
    'BRAVO': 'B',
    'CHARLIE': 'C',
    'DELTA': 'D',
    'ECHO': 'E',
    'FOXTROT': 'F',
    'GOLF': 'G',
    'HOTEL': 'H',
    'INDIA': 'I',
    'JULIET': 'J', 'JULIETT': 'J',
    'KILO': 'K',
    'LIMA': 'L',
    'MIKE': 'M',
    'NOVEMBER': 'N',
    'OSCAR': 'O',
    'PAPA': 'P',
    'QUEBEC': 'Q',
    'ROMEO': 'R',
    'SIERRA': 'S',
    'TANGO': 'T',
    'UNIFORM': 'U',
    'VICTOR': 'V',
    'WHISKEY': 'W',
    'XRAY': 'X', 'X-RAY': 'X',
    'YANKEE': 'Y',
    'ZULU': 'Z',
}

# Phonetic numbers
PHONETIC_NUMBERS = {
    'ZERO': '0', 'ZE-RO': '0',
    'ONE': '1', 'WUN': '1',
    'TWO': '2', 'TOO': '2',
    'THREE': '3', 'TREE': '3',
    'FOUR': '4', 'FOWER': '4',
    'FIVE': '5', 'FIFE': '5',
    'SIX': '6',
    'SEVEN': '7',
    'EIGHT': '8', 'AIT': '8',
    'NINE': '9', 'NINER': '9',
}

# Words that indicate NOT a callsign (taxiways, runways, etc.)
FALSE_POSITIVE_PREFIXES = {
    # Taxiways (single letter designations)
    'TAXIWAY', 'TAXI', 'TWY',
    # Runways
    'RUNWAY', 'RWY', 'RW',
    # Flight levels and altitudes
    'LEVEL', 'FLIGHT LEVEL', 'FL',
    'ALTITUDE', 'ALT',
    # Headings and speeds
    'HEADING', 'HDG',
    'SPEED', 'KNOTS', 'KT',
    # Frequencies
    'FREQUENCY', 'FREQ',
    # Stands and gates
    'STAND', 'GATE', 'APRON',
    # Links and intersections (taxiway designators)
    'LINK', 'HOLD', 'SHORT', 'VIA',
    # General aviation terms
    'SQUAWK', 'TRANSPONDER',
    'DIRECT', 'PROCEED',
    # Approach/departure fixes
    'FIX', 'WAYPOINT', 'VOR', 'NDB',
}

# Words that when followed by a number are NOT callsigns
NOT_CALLSIGN_CONTEXTS = [
    r'\b(?:runway|rwy|rw)\s*\d',
    r'\b(?:flight\s+)?level\s*\d',
    r'\bfl\s*\d',
    r'\b(?:heading|hdg)\s*\d',
    r'\bsquawk\s*\d',
    r'\bstand\s*\d',
    r'\bgate\s*\d',
    r'\bapron\s*\d',
    r'\blink\s*\d',
    r'\bhold\s+short\b',
    r'\bfrequency\s*\d',
    r'\b\d{3}\.\d',  # Frequencies like 121.5
    r'\baltitude\s*\d',
    r'\bspeed\s*\d',
    r'\bknots?\b',
]

# Phonetic alphabet words that look like registrations but aren't
PHONETIC_FALSE_POSITIVES = {
    'X-RAY', 'X RAY', 'XRAY',
    'T-TAG', 'T TAG',
    'I-TAC', 'I TAC',
}


class CallsignExtractor:
    """Extracts and validates callsigns from ATC communications."""

    def __init__(self):
        """Initialize extractor with callsign database."""
        self._callsign_db = {}
        self._cache = get_cache()

    def load_callsigns_from_db(self, db_rows: list) -> None:
        """Load callsign mappings from database rows."""
        for row in db_rows:
            self._callsign_db[row['callsign'].upper()] = (
                row.get('operator', ''),
                row.get('icao', '')
            )

    def load_callsigns_from_csv(self, csv_path: str) -> None:
        """Load callsign mappings from CSV file."""
        import csv
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self._callsign_db[row['callsign'].upper()] = (
                        row.get('operator', ''),
                        row.get('icao', '')
                    )
        except FileNotFoundError:
            pass

    def get_known_callsigns(self) -> List[str]:
        """Get list of known callsign names."""
        return list(self._callsign_db.keys())

    def extract_all(self, text: str) -> List[CallsignMatch]:
        """
        Extract all valid callsigns from text.

        A valid callsign must be:
        1. A known airline name followed by a flight number (e.g., "Shamrock 603")
        2. An aircraft registration (e.g., "N12345", "G-ABCD")

        Args:
            text: Raw transcribed text

        Returns:
            List of CallsignMatch objects
        """
        cache_key = f"callsign_v2:{hash(text)}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        matches = []
        text_upper = text.upper()

        # First, check for false positive contexts
        text_lower = text.lower()
        false_positive_spans = set()
        for pattern in NOT_CALLSIGN_CONTEXTS:
            for match in re.finditer(pattern, text_lower):
                for i in range(match.start(), match.end()):
                    false_positive_spans.add(i)

        # Pattern 1: Known airline name + flight number
        # Flight numbers can be: digits, digits+letter, or spoken as phonetics
        for callsign_name in self._callsign_db.keys():
            # Escape special regex chars and make case insensitive
            escaped_name = re.escape(callsign_name)
            # Match: CALLSIGN + space + (digits or digits+letters)
            pattern = rf'\b{escaped_name}\s+(\d+[A-Z]?|\d+)\b'
            for match in re.finditer(pattern, text_upper, re.IGNORECASE):
                # Check if this overlaps with false positive spans
                if any(i in false_positive_spans for i in range(match.start(), match.end())):
                    continue

                flight_num = match.group(1)
                # Require at least 1 digit in flight number
                if not any(c.isdigit() for c in flight_num):
                    continue

                full_callsign = f"{callsign_name} {flight_num}"
                operator, icao = self._callsign_db.get(callsign_name, (None, None))

                matches.append(CallsignMatch(
                    callsign=full_callsign,
                    operator=operator,
                    icao=icao,
                    confidence=0.95,
                    start_pos=match.start(),
                    end_pos=match.end()
                ))

        # Pattern 2: US registration (N + digits + optional letters)
        # Must be N followed by 1-5 digits and 0-2 letters
        us_reg_pattern = r'\b(N\d{1,5}[A-Z]{0,2})\b'
        for match in re.finditer(us_reg_pattern, text_upper):
            if any(i in false_positive_spans for i in range(match.start(), match.end())):
                continue
            reg = match.group(1)
            # Validate: must have at least 2 digits after N
            digits = sum(1 for c in reg if c.isdigit())
            if digits >= 2:
                matches.append(CallsignMatch(
                    callsign=reg,
                    operator=None,
                    icao=None,
                    confidence=0.9,
                    start_pos=match.start(),
                    end_pos=match.end()
                ))

        # Pattern 3: European registration (X-XXXX or XX-XXX)
        eu_reg_pattern = r'\b([A-Z]{1,2}-[A-Z]{3,4})\b'
        for match in re.finditer(eu_reg_pattern, text_upper):
            if any(i in false_positive_spans for i in range(match.start(), match.end())):
                continue
            reg = match.group(1)
            # Skip phonetic alphabet false positives
            if reg in PHONETIC_FALSE_POSITIVES or reg.replace('-', ' ') in PHONETIC_FALSE_POSITIVES:
                continue
            matches.append(CallsignMatch(
                callsign=reg,
                operator=None,
                icao=None,
                confidence=0.9,
                start_pos=match.start(),
                end_pos=match.end()
            ))

        # Deduplicate overlapping matches
        matches = self._deduplicate_matches(matches)
        matches.sort(key=lambda m: m.start_pos)

        self._cache.set(cache_key, matches, ttl=3600)
        return matches

    def extract_primary(self, text: str) -> Optional[CallsignMatch]:
        """Extract the most likely primary callsign from text."""
        matches = self.extract_all(text)
        if not matches:
            return None
        # Return highest confidence match
        return max(matches, key=lambda m: m.confidence)

    def _deduplicate_matches(self, matches: List[CallsignMatch]) -> List[CallsignMatch]:
        """Remove overlapping matches, keeping highest confidence."""
        if not matches:
            return []

        sorted_matches = sorted(matches, key=lambda m: m.start_pos)
        result = []

        for match in sorted_matches:
            overlaps = False
            for i, existing in enumerate(result):
                if (match.start_pos < existing.end_pos and
                    match.end_pos > existing.start_pos):
                    overlaps = True
                    if match.confidence > existing.confidence:
                        result[i] = match
                    break

            if not overlaps:
                result.append(match)

        return result


# Module-level convenience functions
_default_extractor = None


def get_extractor() -> CallsignExtractor:
    """Get or create the default callsign extractor."""
    global _default_extractor
    if _default_extractor is None:
        _default_extractor = CallsignExtractor()
        _default_extractor.load_callsigns_from_csv('callsigns.csv')
        # Also try to load from database
        try:
            from processor.db import query_all
            rows = query_all("SELECT callsign, operator, icao FROM callsign_mappings")
            _default_extractor.load_callsigns_from_db(rows)
        except Exception:
            pass  # Table might not exist yet
    return _default_extractor


def reload_extractor() -> None:
    """Force reload of the callsign extractor."""
    global _default_extractor
    _default_extractor = None
    get_extractor()


def extract_callsign(text: str) -> Optional[str]:
    """
    Extract primary callsign from text.

    Args:
        text: Transcribed message text

    Returns:
        Callsign string or None if not found
    """
    match = get_extractor().extract_primary(text)
    return match.callsign if match else None


def extract_callsign_with_metadata(text: str) -> Optional[CallsignMatch]:
    """
    Extract primary callsign with full metadata.

    Args:
        text: Transcribed message text

    Returns:
        CallsignMatch object or None
    """
    return get_extractor().extract_primary(text)
