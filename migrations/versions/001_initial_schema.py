"""
Initial database schema.

Creates the messages table with all current columns.
This migration represents the baseline schema.
"""

import sqlite3


def upgrade(conn: sqlite3.Connection) -> None:
    """Create initial messages table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            text TEXT,
            callsign TEXT,
            operator TEXT,
            route TEXT,
            speaker TEXT,
            confidence REAL
        )
    """)
    conn.commit()


def downgrade(conn: sqlite3.Connection) -> None:
    """Drop messages table."""
    conn.execute("DROP TABLE IF EXISTS messages")
    conn.commit()
