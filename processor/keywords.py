"""
Keyword detection for safety-critical ATC communications.

Detects emergency keywords, unusual situations, and alerts.
"""

from typing import List
from processor.cache import get_cache


# Priority keywords indicating emergencies or critical situations
EMERGENCY_KEYWORDS = [
    "mayday",
    "pan pan",
    "pan-pan",
    "emergency",
    "declare emergency",
    "fuel emergency",
    "medical emergency",
]

# Keywords indicating potential issues
ALERT_KEYWORDS = [
    "unable",
    "negative",
    "say again",
    "repeat",
    "go around",
    "go-around",
    "missed approach",
    "divert",
    "diverting",
    "minimum fuel",
    "low fuel",
    "bird strike",
    "traffic alert",
    "terrain",
    "pull up",
    "windshear",
    "wind shear",
    "tcas",
    "resolution advisory",
]

# Keywords indicating quality issues (accents, speed, clarity)
QUALITY_KEYWORDS = [
    "say again",
    "repeat",
    "confirm",
    "verify",
    "unreadable",
    "broken",
    "garbled",
    "blocked",
    "stepped on",
]

# All keywords combined for general detection
ALL_KEYWORDS = EMERGENCY_KEYWORDS + ALERT_KEYWORDS + QUALITY_KEYWORDS


def detect_keywords(text: str) -> List[str]:
    """
    Detect safety-critical keywords in message text.

    Args:
        text: Message text to analyze

    Returns:
        List of detected keywords
    """
    cache = get_cache()
    cache_key = f"keywords:{hash(text)}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    text_lower = text.lower()
    found = []

    for keyword in ALL_KEYWORDS:
        if keyword in text_lower:
            found.append(keyword)

    cache.set(cache_key, found, ttl=3600)
    return found


def detect_emergency(text: str) -> bool:
    """Check if text contains emergency keywords."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in EMERGENCY_KEYWORDS)


def detect_quality_issues(text: str) -> bool:
    """Check if text indicates communication quality problems."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in QUALITY_KEYWORDS)


def get_keyword_severity(keywords: List[str]) -> str:
    """
    Get severity level based on detected keywords.

    Returns:
        'emergency', 'alert', 'quality', or 'normal'
    """
    if not keywords:
        return 'normal'

    for kw in keywords:
        if kw in EMERGENCY_KEYWORDS:
            return 'emergency'

    for kw in keywords:
        if kw in ALERT_KEYWORDS:
            return 'alert'

    return 'quality'
