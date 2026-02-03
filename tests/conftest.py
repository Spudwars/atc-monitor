"""
Pytest fixtures for ATC Monitor tests.

Provides:
- Isolated test database
- Cache reset between tests
- Sample data fixtures
"""

import os
import tempfile
import pytest

from processor import db
from processor.cache import Cache, set_cache


@pytest.fixture
def temp_db():
    """
    Create a temporary database for testing.

    Yields the database path, cleans up after test.
    """
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Override the DB path
    original_path = db.DB_PATH
    db.set_db_path(path)

    # Initialize schema
    conn = db.get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            text TEXT,
            callsign TEXT,
            operator TEXT,
            route TEXT,
            speaker TEXT,
            confidence REAL,
            conversation_id TEXT,
            audio_file TEXT,
            audio_offset_ms INTEGER,
            icao_code TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

    yield path

    # Cleanup
    db.set_db_path(original_path)
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def fresh_cache():
    """
    Provide a fresh cache instance for each test.

    Resets global cache after test.
    """
    cache = Cache(default_ttl=60, max_size=100)
    set_cache(cache)
    yield cache
    set_cache(None)


@pytest.fixture
def sample_messages():
    """Sample ATC messages for testing."""
    return [
        {
            'text': 'Speedbird 123 descend flight level 280',
            'expected_speaker': 'TOWER',
            'expected_callsign': 'SPEEDBIRD 123',
        },
        {
            'text': 'Speedbird 123 descending flight level 280',
            'expected_speaker': 'AIRCRAFT',
            'expected_callsign': 'SPEEDBIRD 123',
        },
        {
            'text': 'Ryanair 456 cleared to land runway 27 left',
            'expected_speaker': 'TOWER',
            'expected_callsign': 'RYANAIR 456',
        },
        {
            'text': 'Ryanair 456 cleared to land runway 27 left wilco',
            'expected_speaker': 'AIRCRAFT',  # wilco indicates pilot
            'expected_callsign': 'RYANAIR 456',
        },
        {
            'text': 'November 1 2 3 Alpha Bravo requesting taxi',
            'expected_speaker': 'AIRCRAFT',
            'expected_callsign': 'N123AB',
        },
        {
            'text': 'Golf Alpha Bravo Charlie Delta contact tower 118.7',
            'expected_speaker': 'TOWER',
            'expected_callsign': 'G-ABCD',
        },
    ]


@pytest.fixture
def populated_db(temp_db, sample_messages):
    """
    Database populated with sample messages.

    Returns list of inserted message IDs.
    """
    ids = []
    for msg in sample_messages:
        msg_id = db.save_message(
            text=msg['text'],
            timestamp='2024-01-01T12:00:00Z',
        )
        ids.append(msg_id)
    return ids
