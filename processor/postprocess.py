"""
Post-processing module for ATC message analysis.

Analyzes transcribed messages to extract:
- Speaker role (Tower/Controller vs Aircraft/Pilot)
- Callsigns and operators
- Safety-critical keywords
- Conversation threading
"""

from processor.db import query_all, update_message_analysis
from processor.callsign import extract_callsign_with_metadata
from processor.keywords import detect_keywords, get_keyword_severity
from processor.cache import get_cache


# Phrases that indicate controller/tower speech
TOWER_INDICATORS = [
    # Instructions
    "descend", "climb", "maintain", "reduce speed", "increase speed",
    "turn left", "turn right", "fly heading", "direct to",
    "hold short", "line up and wait", "cleared to land", "cleared for takeoff",
    "go around", "abort", "hold position", "give way", "follow",
    "contact tower", "contact approach", "contact departure", "contact ground",
    "squawk", "ident", "recycle", "reset transponder",
    # Clearances
    "cleared", "approved", "authorized", "expect", "advise",
    "report", "confirm", "verify", "say again", "read back",
    # Traffic/weather
    "traffic", "caution", "wake turbulence", "wind", "visibility",
    "runway", "taxiway", "apron", "gate",
]

# Phrases that indicate pilot/aircraft speech
AIRCRAFT_INDICATORS = [
    # Readbacks and acknowledgments
    "wilco", "roger", "affirm", "negative", "unable",
    "with you", "checking in", "level", "passing", "for",
    # Requests
    "request", "requesting", "looking for", "need",
    # Position reports
    "established", "inbound", "outbound", "downwind", "base", "final",
    "departing", "arriving",
]


def detect_speaker(text: str) -> str:
    """
    Detect whether message is from Tower/Controller or Aircraft/Pilot.

    Uses keyword matching with weighted scoring.

    Args:
        text: Message text

    Returns:
        "TOWER" or "AIRCRAFT"
    """
    cache = get_cache()
    cache_key = f"speaker:{hash(text)}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    t = text.lower()

    tower_score = 0
    aircraft_score = 0

    for phrase in TOWER_INDICATORS:
        if phrase in t:
            tower_score += 1

    for phrase in AIRCRAFT_INDICATORS:
        if phrase in t:
            aircraft_score += 1

    # Default to AIRCRAFT if no clear signal (pilots speak more often)
    if tower_score > aircraft_score:
        result = "TOWER"
    else:
        result = "AIRCRAFT"

    cache.set(cache_key, result, ttl=3600)  # Cache for 1 hour
    return result


def analyze_message(message_id: int, text: str) -> dict:
    """
    Perform full analysis on a message.

    Args:
        message_id: Database message ID
        text: Message text

    Returns:
        Dict with extracted fields
    """
    # Detect speaker
    speaker = detect_speaker(text)

    # Extract callsign
    callsign_match = extract_callsign_with_metadata(text)

    # Detect keywords
    keywords = detect_keywords(text)
    severity = get_keyword_severity(keywords)

    # Use empty string (not None) to clear old values
    result = {
        'speaker': speaker,
        'callsign': '',  # Clear if no match
        'operator': '',
        'icao_code': '',
        'keywords': keywords,
        'severity': severity,
    }

    if callsign_match:
        result['callsign'] = callsign_match.callsign
        result['operator'] = callsign_match.operator or ''
        result['icao_code'] = callsign_match.icao or ''

    return result


def reanalyze_messages() -> int:
    """
    Re-run analysis on all messages in the database.

    Updates speaker, callsign, operator, and icao_code fields.
    Handles both 'text' and 'message' column names for compatibility.

    Returns:
        Number of messages processed
    """
    # Try both column names for compatibility with different schemas
    try:
        rows = query_all("SELECT id, text FROM messages")
        text_col = 'text'
    except Exception:
        rows = query_all("SELECT id, message as text FROM messages")
        text_col = 'text'

    count = 0
    for row in rows:
        message_id = row['id']
        text = row[text_col] or ''

        analysis = analyze_message(message_id, text)

        update_message_analysis(
            message_id,
            callsign=analysis['callsign'],
            operator=analysis['operator'],
            icao_code=analysis.get('icao_code'),
            speaker=analysis['speaker'],
            keywords=','.join(analysis.get('keywords', [])),
        )
        count += 1

    print(f"Reanalyzed {count} messages")
    return count
