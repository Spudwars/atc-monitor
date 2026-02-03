"""
Add fields for conversation threading and audio references.

Adds:
- conversation_id: Links messages in the same conversation thread
- audio_file: Reference to source audio file
- audio_offset_ms: Timestamp within audio file
- icao_code: ICAO airline code for the callsign
"""

import sqlite3


def upgrade(conn: sqlite3.Connection) -> None:
    """Add conversation and audio reference columns."""
    cursor = conn.cursor()

    # Check which columns already exist
    cursor.execute("PRAGMA table_info(messages)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("conversation_id", "TEXT"),
        ("audio_file", "TEXT"),
        ("audio_offset_ms", "INTEGER"),
        ("icao_code", "TEXT"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            cursor.execute(
                f"ALTER TABLE messages ADD COLUMN {col_name} {col_type}"
            )

    # Create index for conversation lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_conversation
        ON messages(conversation_id)
    """)

    # Create index for timestamp-based queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_timestamp
        ON messages(timestamp)
    """)

    conn.commit()


def downgrade(conn: sqlite3.Connection) -> None:
    """
    SQLite doesn't support DROP COLUMN before 3.35.
    For older versions, we'd need to recreate the table.
    For simplicity, we just drop the indexes.
    """
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS idx_messages_conversation")
    cursor.execute("DROP INDEX IF EXISTS idx_messages_timestamp")
    conn.commit()
