"""
Database layer for ATC Monitor.

Provides centralized database access with connection management,
query helpers, and transaction support.
"""

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

# Database path - can be overridden for testing
DB_PATH = "data/atc_messages.db"

# Thread-local storage for connections
_local = threading.local()


def get_db_path() -> str:
    """Get the current database path."""
    return getattr(_local, 'db_path', DB_PATH)


def set_db_path(path: str) -> None:
    """Set database path (useful for testing)."""
    _local.db_path = path


def get_connection() -> sqlite3.Connection:
    """
    Get a database connection.

    Creates the data directory if needed and returns a connection
    with row_factory set for dict-like access.
    """
    db_path = get_db_path()

    # Ensure data directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """
    Context manager for database transactions.

    Automatically commits on success, rolls back on exception.

    Usage:
        with transaction() as conn:
            conn.execute("INSERT INTO ...")
            conn.execute("UPDATE ...")
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def readonly() -> Iterator[sqlite3.Connection]:
    """
    Context manager for read-only database access.

    Usage:
        with readonly() as conn:
            rows = conn.execute("SELECT ...").fetchall()
    """
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """
    Initialize the database schema.

    Runs all pending migrations to ensure schema is up to date.
    """
    # Import here to avoid circular dependency
    from migrations.runner import run_migrations
    run_migrations()


def query_one(
    sql: str,
    params: tuple = ()
) -> Optional[sqlite3.Row]:
    """
    Execute a query and return a single row.

    Args:
        sql: SQL query string
        params: Query parameters

    Returns:
        Single Row or None if not found
    """
    with readonly() as conn:
        cursor = conn.execute(sql, params)
        return cursor.fetchone()


def query_all(
    sql: str,
    params: tuple = ()
) -> list[sqlite3.Row]:
    """
    Execute a query and return all rows.

    Args:
        sql: SQL query string
        params: Query parameters

    Returns:
        List of Row objects
    """
    with readonly() as conn:
        cursor = conn.execute(sql, params)
        return cursor.fetchall()


def execute(sql: str, params: tuple = ()) -> int:
    """
    Execute a write query and return affected row count.

    Args:
        sql: SQL query string
        params: Query parameters

    Returns:
        Number of affected rows
    """
    with transaction() as conn:
        cursor = conn.execute(sql, params)
        return cursor.rowcount


def insert(table: str, data: dict[str, Any]) -> int:
    """
    Insert a row and return the new row ID.

    Args:
        table: Table name
        data: Column name to value mapping

    Returns:
        ID of inserted row
    """
    columns = ', '.join(data.keys())
    placeholders = ', '.join('?' * len(data))
    sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

    with transaction() as conn:
        cursor = conn.execute(sql, tuple(data.values()))
        return cursor.lastrowid


def update(
    table: str,
    data: dict[str, Any],
    where: str,
    where_params: tuple = ()
) -> int:
    """
    Update rows matching a condition.

    Args:
        table: Table name
        data: Column name to new value mapping
        where: WHERE clause (without 'WHERE' keyword)
        where_params: Parameters for WHERE clause

    Returns:
        Number of updated rows
    """
    set_clause = ', '.join(f"{k} = ?" for k in data.keys())
    sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
    params = tuple(data.values()) + where_params

    with transaction() as conn:
        cursor = conn.execute(sql, params)
        return cursor.rowcount


# Message-specific helpers

def get_message(message_id: int) -> Optional[sqlite3.Row]:
    """Get a message by ID."""
    return query_one(
        "SELECT * FROM messages WHERE id = ?",
        (message_id,)
    )


def get_messages(
    limit: int = 100,
    offset: int = 0,
    callsign: Optional[str] = None,
    speaker: Optional[str] = None,
    conversation_id: Optional[str] = None
) -> list[sqlite3.Row]:
    """
    Get messages with optional filters.

    Args:
        limit: Maximum rows to return
        offset: Number of rows to skip
        callsign: Filter by callsign
        speaker: Filter by speaker (TOWER/AIRCRAFT)
        conversation_id: Filter by conversation

    Returns:
        List of message rows
    """
    conditions = []
    params = []

    if callsign:
        conditions.append("callsign = ?")
        params.append(callsign)
    if speaker:
        conditions.append("speaker = ?")
        params.append(speaker)
    if conversation_id:
        conditions.append("conversation_id = ?")
        params.append(conversation_id)

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT * FROM messages
        {where}
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    return query_all(sql, tuple(params))


def save_message(
    text: str,
    timestamp: str,
    callsign: Optional[str] = None,
    operator: Optional[str] = None,
    speaker: Optional[str] = None,
    confidence: Optional[float] = None,
    audio_file: Optional[str] = None,
    audio_offset_ms: Optional[int] = None
) -> int:
    """
    Save a new message.

    Returns the new message ID.
    """
    return insert('messages', {
        'text': text,
        'timestamp': timestamp,
        'callsign': callsign,
        'operator': operator,
        'speaker': speaker,
        'confidence': confidence,
        'audio_file': audio_file,
        'audio_offset_ms': audio_offset_ms,
    })


def update_message_analysis(
    message_id: int,
    callsign: Optional[str] = None,
    operator: Optional[str] = None,
    icao_code: Optional[str] = None,
    speaker: Optional[str] = None,
    conversation_id: Optional[str] = None
) -> int:
    """
    Update analysis fields on an existing message.

    Only updates fields that are provided (not None).
    """
    data = {}
    if callsign is not None:
        data['callsign'] = callsign
    if operator is not None:
        data['operator'] = operator
    if icao_code is not None:
        data['icao_code'] = icao_code
    if speaker is not None:
        data['speaker'] = speaker
    if conversation_id is not None:
        data['conversation_id'] = conversation_id

    if not data:
        return 0

    return update('messages', data, 'id = ?', (message_id,))
