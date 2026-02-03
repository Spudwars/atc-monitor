"""
Simple migration runner for SQLite database.

Tracks applied migrations in a schema_migrations table and applies
pending migrations in order.
"""

import sqlite3
import importlib
import pkgutil
from pathlib import Path
from typing import List, Tuple

from processor.db import get_connection, DB_PATH


def get_applied_migrations(conn: sqlite3.Connection) -> set[str]:
    """Get set of already-applied migration names."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    cursor.execute("SELECT version FROM schema_migrations")
    return {row[0] for row in cursor.fetchall()}


def get_pending_migrations() -> List[Tuple[str, object]]:
    """
    Discover migration modules in migrations/versions/.

    Returns list of (version_name, module) tuples sorted by version.
    """
    versions_path = Path(__file__).parent / "versions"
    if not versions_path.exists():
        versions_path.mkdir(parents=True)
        return []

    migrations = []
    for finder, name, ispkg in pkgutil.iter_modules([str(versions_path)]):
        if name.startswith('_'):
            continue
        module = importlib.import_module(f"migrations.versions.{name}")
        if hasattr(module, 'upgrade'):
            migrations.append((name, module))

    # Sort by version name (assumes format: 001_description, 002_description, etc.)
    migrations.sort(key=lambda x: x[0])
    return migrations


def run_migrations() -> List[str]:
    """
    Run all pending migrations.

    Returns list of applied migration names.
    """
    conn = get_connection()
    applied = get_applied_migrations(conn)
    pending = get_pending_migrations()

    newly_applied = []

    for version, module in pending:
        if version in applied:
            continue

        print(f"Applying migration: {version}")
        try:
            module.upgrade(conn)
            conn.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)",
                (version,)
            )
            conn.commit()
            newly_applied.append(version)
            print(f"  Applied: {version}")
        except Exception as e:
            conn.rollback()
            print(f"  Failed: {version} - {e}")
            raise

    conn.close()

    if not newly_applied:
        print("No pending migrations.")

    return newly_applied


def rollback_last() -> str | None:
    """
    Rollback the most recently applied migration.

    Returns the rolled-back migration name or None.
    """
    conn = get_connection()
    applied = get_applied_migrations(conn)

    if not applied:
        print("No migrations to rollback.")
        conn.close()
        return None

    # Get most recent
    cursor = conn.cursor()
    cursor.execute(
        "SELECT version FROM schema_migrations ORDER BY applied_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    version = row[0]

    # Find the module
    pending = get_pending_migrations()
    module = None
    for v, m in pending:
        if v == version:
            module = m
            break

    if module and hasattr(module, 'downgrade'):
        print(f"Rolling back: {version}")
        try:
            module.downgrade(conn)
            conn.execute(
                "DELETE FROM schema_migrations WHERE version = ?",
                (version,)
            )
            conn.commit()
            print(f"  Rolled back: {version}")
            conn.close()
            return version
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"  Rollback failed: {version} - {e}")
            raise
    else:
        print(f"No downgrade available for: {version}")
        conn.close()
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_last()
    else:
        run_migrations()
