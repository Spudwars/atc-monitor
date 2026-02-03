"""
Post-processing module for ATC message analysis.

Analyzes transcribed messages to extract:
- Speaker role (Tower/Controller vs Aircraft/Pilot)
- Callsigns and operators
- Conversation threading
"""

from processor.db import query_all, update_message_analysis
from processor.callsign import extract_callsign_with_metadata
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

    result = {
        'speaker': speaker,
        'callsign': None,
        'operator': None,
        'icao_code': None,
    }

    if callsign_match:
        result['callsign'] = callsign_match.callsign
        result['operator'] = callsign_match.operator
        result['icao_code'] = callsign_match.icao

    return result


def reanalyze_messages() -> int:
    """
    Re-run analysis on all messages in the database.

    Updates speaker, callsign, operator, and icao_code fields.

    Returns:
        Number of messages processed
    """
    rows = query_all("SELECT id, text FROM messages")

    count = 0
    for row in rows:
        message_id = row['id']
        text = row['text']

        analysis = analyze_message(message_id, text)

        update_message_analysis(
            message_id,
            callsign=analysis['callsign'],
            operator=analysis['operator'],
            icao_code=analysis['icao_code'],
            speaker=analysis['speaker'],
        )
        count += 1

    print(f"Reanalyzed {count} messages")
    return count
