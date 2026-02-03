"""
Add fields for keywords, severity, and airport.

Adds:
- keywords: Comma-separated list of detected keywords
- severity: Alert level (emergency, alert, quality, normal)
- airport: Airport ICAO code (e.g., EIDW, EGLL)
- source_file: Original audio file name
- timestamp_start: Start time in audio file (seconds)
- timestamp_end: End time in audio file (seconds)
"""

import sqlite3


def upgrade(conn: sqlite3.Connection) -> None:
    """Add keyword and audio-related columns."""
    cursor = conn.cursor()

    # Check which columns already exist
    cursor.execute("PRAGMA table_info(messages)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("keywords", "TEXT"),
        ("severity", "TEXT DEFAULT 'normal'"),
        ("airport", "TEXT"),
        ("source_file", "TEXT"),
        ("timestamp_start", "REAL"),
        ("timestamp_end", "REAL"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            cursor.execute(
                f"ALTER TABLE messages ADD COLUMN {col_name} {col_type}"
            )

    # Create index for keyword searches
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_keywords
        ON messages(keywords)
    """)

    # Create index for airport lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_airport
        ON messages(airport)
    """)

    conn.commit()


def downgrade(conn: sqlite3.Connection) -> None:
    """Drop indexes (columns can't be easily dropped in SQLite)."""
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS idx_messages_keywords")
    cursor.execute("DROP INDEX IF EXISTS idx_messages_airport")
    conn.commit()
