"""
ATC Monitor CLI entry point.

Usage:
    python main.py              # Initialize database
    python main.py --reanalyze  # Re-run analysis on existing messages
    python main.py --migrate    # Run pending migrations
"""

import argparse
from processor.db import init_db
from processor.postprocess import reanalyze_messages


def main():
    parser = argparse.ArgumentParser(
        description="ATC Monitor - Aviation communications analysis"
    )
    parser.add_argument(
        "--reanalyze",
        action="store_true",
        help="Re-analyze all messages in the database"
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Run pending database migrations"
    )
    args = parser.parse_args()

    # Initialize/migrate database
    print("Initializing database...")
    init_db()

    if args.reanalyze:
        print("Re-analyzing messages...")
        count = reanalyze_messages()
        print(f"Done. Processed {count} messages.")
    elif not args.migrate:
        print("Database initialized. Use --reanalyze to process messages.")
        print("Run 'python -m web.webapp' to start the web interface.")


if __name__ == "__main__":
    main()
