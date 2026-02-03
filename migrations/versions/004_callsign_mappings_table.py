"""
Create callsign_mappings table for managing airline callsigns.

Stores the mapping between radio callsigns and airline details,
replacing the CSV file approach.
"""

import sqlite3
import csv
import os


def upgrade(conn: sqlite3.Connection) -> None:
    """Create callsign_mappings table and migrate data from CSV."""
    cursor = conn.cursor()

    # Create the table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS callsign_mappings (
            id INTEGER PRIMARY KEY,
            callsign TEXT UNIQUE NOT NULL,
            operator TEXT,
            icao TEXT,
            country TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create index for fast lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_callsign_mappings_callsign
        ON callsign_mappings(callsign)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_callsign_mappings_icao
        ON callsign_mappings(icao)
    """)

    # Migrate data from CSV if it exists
    csv_path = 'callsigns.csv'
    if os.path.exists(csv_path):
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO callsign_mappings (callsign, operator, icao)
                        VALUES (?, ?, ?)
                    """, (
                        row['callsign'].upper(),
                        row.get('operator', ''),
                        row.get('icao', '')
                    ))
                except Exception:
                    pass  # Skip invalid rows

    conn.commit()


def downgrade(conn: sqlite3.Connection) -> None:
    """Drop callsign_mappings table."""
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS callsign_mappings")
    conn.commit()
