"""
Callsign extraction module with regex + fuzzy matching for aviation communications.

Handles various callsign formats:
- Airline callsigns: SPEEDBIRD 123, RYANAIR 456
- ICAO format: BAW123, RYR456
- General aviation: N12345, G-ABCD
- Military: VIPER 01, MAGIC 42
"""

import re
from dataclasses import dataclass
from typing import Optional
from functools import lru_cache

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
    'HUNDRED': '00',
    'THOUSAND': '000',
}

# Regex patterns for different callsign types
PATTERNS = {
    # Airline callsign with flight number: SPEEDBIRD 123, RYANAIR 4 5 6
    'airline': re.compile(
        r'\b([A-Z][A-Z]+)\s+(\d[\d\s]*\d|\d)\b',
        re.IGNORECASE
    ),
    # ICAO 3-letter code + numbers: BAW123, RYR456
    'icao': re.compile(
        r'\b([A-Z]{3})(\d{1,4}[A-Z]?)\b',
        re.IGNORECASE
    ),
    # US registration: N12345, N123AB
    'us_registration': re.compile(
        r'\b(N\d{1,5}[A-Z]{0,2})\b',
        re.IGNORECASE
    ),
    # UK/European registration: G-ABCD, D-EFGH
    'eu_registration': re.compile(
        r'\b([A-Z]{1,2}-[A-Z]{3,4})\b',
        re.IGNORECASE
    ),
    # Military callsign: VIPER 01, MAGIC 42
    'military': re.compile(
        r'\b([A-Z]+)\s+(ZERO\s+)?(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|NINER|\d+)\b',
        re.IGNORECASE
    ),
}


class CallsignExtractor:
    """Extracts and normalizes callsigns from ATC communications."""

    def __init__(self, callsign_db: dict = None):
        """
        Initialize extractor with optional callsign database.

        Args:
            callsign_db: Dict mapping callsign names to (operator, icao) tuples
        """
        self._callsign_db = callsign_db or {}
        self._cache = get_cache()

    def load_callsigns_from_csv(self, csv_path: str) -> None:
        """Load callsign mappings from CSV file."""
        import csv
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self._callsign_db[row['callsign'].upper()] = (
                    row.get('operator', ''),
                    row.get('icao', '')
                )

    def normalize_phonetic(self, text: str) -> str:
        """Convert phonetic alphabet/numbers to standard form."""
        words = text.upper().split()
        result = []
        for word in words:
            if word in PHONETIC_ALPHABET:
                result.append(PHONETIC_ALPHABET[word])
            elif word in PHONETIC_NUMBERS:
                result.append(PHONETIC_NUMBERS[word])
            else:
                result.append(word)
        return ' '.join(result)

    def extract_all(self, text: str) -> list[CallsignMatch]:
        """
        Extract all callsigns from text.

        Args:
            text: Raw transcribed text

        Returns:
            List of CallsignMatch objects, sorted by position
        """
        cache_key = f"callsign_extract:{hash(text)}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        matches = []
        normalized = self.normalize_phonetic(text)

        # Try each pattern type
        for pattern_name, pattern in PATTERNS.items():
            for match in pattern.finditer(normalized):
                callsign_match = self._process_match(
                    match, pattern_name, text
                )
                if callsign_match:
                    matches.append(callsign_match)

        # Remove overlapping matches, keeping highest confidence
        matches = self._deduplicate_matches(matches)
        matches.sort(key=lambda m: m.start_pos)

        self._cache.set(cache_key, matches)
        return matches

    def extract_primary(self, text: str) -> Optional[CallsignMatch]:
        """Extract the most likely primary callsign from text."""
        matches = self.extract_all(text)
        if not matches:
            return None
        # Return highest confidence match
        return max(matches, key=lambda m: m.confidence)

    def _process_match(
        self, match: re.Match, pattern_type: str, original_text: str
    ) -> Optional[CallsignMatch]:
        """Process a regex match into a CallsignMatch."""
        if pattern_type == 'airline':
            name = match.group(1).upper()
            number = re.sub(r'\s+', '', match.group(2))
            callsign = f"{name} {number}"

            # Look up in database
            operator, icao = self._callsign_db.get(name, (None, None))
            confidence = 0.9 if operator else 0.6

            return CallsignMatch(
                callsign=callsign,
                operator=operator,
                icao=icao,
                confidence=confidence,
                start_pos=match.start(),
                end_pos=match.end()
            )

        elif pattern_type == 'icao':
            icao_code = match.group(1).upper()
            number = match.group(2).upper()
            callsign = f"{icao_code}{number}"

            # Reverse lookup by ICAO
            operator = None
            for name, (op, code) in self._callsign_db.items():
                if code == icao_code:
                    operator = op
                    break

            return CallsignMatch(
                callsign=callsign,
                operator=operator,
                icao=icao_code,
                confidence=0.85,
                start_pos=match.start(),
                end_pos=match.end()
            )

        elif pattern_type in ('us_registration', 'eu_registration'):
            registration = match.group(1).upper()
            return CallsignMatch(
                callsign=registration,
                operator=None,
                icao=None,
                confidence=0.95,  # Registrations are very distinctive
                start_pos=match.start(),
                end_pos=match.end()
            )

        elif pattern_type == 'military':
            name = match.group(1).upper()
            # Reconstruct number from phonetics
            number_part = match.group(3)
            if number_part:
                number = PHONETIC_NUMBERS.get(number_part.upper(), number_part)
            else:
                number = ''
            if match.group(2):  # ZERO prefix
                number = '0' + number
            callsign = f"{name} {number}".strip()

            return CallsignMatch(
                callsign=callsign,
                operator=None,
                icao=None,
                confidence=0.5,  # Military callsigns harder to verify
                start_pos=match.start(),
                end_pos=match.end()
            )

        return None

    def _deduplicate_matches(
        self, matches: list[CallsignMatch]
    ) -> list[CallsignMatch]:
        """Remove overlapping matches, keeping highest confidence."""
        if not matches:
            return []

        # Sort by start position
        sorted_matches = sorted(matches, key=lambda m: m.start_pos)
        result = []

        for match in sorted_matches:
            # Check if overlaps with any existing result
            overlaps = False
            for i, existing in enumerate(result):
                if (match.start_pos < existing.end_pos and
                    match.end_pos > existing.start_pos):
                    overlaps = True
                    # Keep higher confidence
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
        try:
            _default_extractor.load_callsigns_from_csv('callsigns.csv')
        except FileNotFoundError:
            pass
    return _default_extractor


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
