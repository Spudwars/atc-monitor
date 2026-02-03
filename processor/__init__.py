"""
ATC Monitor processor package.

Provides:
- db: Database access layer
- postprocess: Message analysis (speaker detection, callsign extraction)
- callsign: Callsign extraction and normalization
- keywords: Safety-critical keyword detection
- cache: In-memory caching
"""

from processor.db import init_db, get_connection
from processor.postprocess import reanalyze_messages, detect_speaker
from processor.callsign import extract_callsign
from processor.keywords import detect_keywords, detect_emergency

__all__ = [
    'init_db',
    'get_connection',
    'reanalyze_messages',
    'detect_speaker',
    'extract_callsign',
    'detect_keywords',
    'detect_emergency',
]
