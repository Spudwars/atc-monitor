"""
Utility functions for ATC Monitor.

Includes timestamp conversion, filename parsing, and other helpers.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple


# Month name to number mapping
MONTHS = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
}


def parse_recording_filename(filename: str) -> Optional[datetime]:
    """
    Parse recording start time from filename.

    Expected formats:
    - EIDW8-Gnd-Twr-App-Ctr-Sep-25-2025-0000Z.mp3
    - EGLL-Tower-Jan-15-2024-1430Z.wav

    Returns:
        datetime object in UTC or None if parsing fails
    """
    if not filename:
        return None

    # Pattern: Month-Day-Year-TimeZ
    # e.g., Sep-25-2025-0000Z
    pattern = r'([A-Za-z]{3})-(\d{1,2})-(\d{4})-(\d{4})Z'
    match = re.search(pattern, filename)

    if not match:
        return None

    try:
        month_str = match.group(1).lower()
        day = int(match.group(2))
        year = int(match.group(3))
        time_str = match.group(4)

        month = MONTHS.get(month_str)
        if not month:
            return None

        hour = int(time_str[:2])
        minute = int(time_str[2:])

        return datetime(year, month, day, hour, minute, 0)
    except (ValueError, IndexError):
        return None


def offset_to_utc(filename: str, offset_seconds: float) -> Optional[datetime]:
    """
    Convert audio offset to UTC timestamp.

    Args:
        filename: Recording filename containing start time
        offset_seconds: Offset in seconds from start of recording

    Returns:
        UTC datetime or None if cannot be calculated
    """
    start_time = parse_recording_filename(filename)
    if not start_time:
        return None

    return start_time + timedelta(seconds=offset_seconds)


def format_utc_time(dt: Optional[datetime]) -> str:
    """Format datetime as UTC string."""
    if not dt:
        return ""
    return dt.strftime("%H:%M:%SZ")


def format_utc_datetime(dt: Optional[datetime]) -> str:
    """Format datetime as full UTC datetime string."""
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%SZ")


def seconds_to_timecode(seconds: float) -> str:
    """
    Convert seconds to timecode format (HH:MM:SS).

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timecode string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def get_audio_context_url(source_file: str, offset_start: float, context_seconds: int = 30) -> str:
    """
    Generate URL for audio with context around a specific offset.

    Args:
        source_file: Audio filename
        offset_start: Start offset in seconds
        context_seconds: Seconds of context before/after

    Returns:
        URL with time fragment
    """
    # Calculate start time with context (don't go below 0)
    start = max(0, offset_start - context_seconds)
    return f"/audio/{source_file}#t={start:.1f}"
