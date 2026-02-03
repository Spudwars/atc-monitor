"""Tests for database layer."""

import pytest
from processor import db


class TestConnection:
    """Test database connection management."""

    def test_get_connection(self, temp_db):
        conn = db.get_connection()
        assert conn is not None
        conn.close()

    def test_connection_has_row_factory(self, temp_db):
        conn = db.get_connection()
        cursor = conn.execute("SELECT 1 as value")
        row = cursor.fetchone()
        assert row['value'] == 1
        conn.close()


class TestTransactions:
    """Test transaction context managers."""

    def test_transaction_commits_on_success(self, temp_db):
        with db.transaction() as conn:
            conn.execute(
                "INSERT INTO messages (text, timestamp) VALUES (?, ?)",
                ("Test message", "2024-01-01T00:00:00Z")
            )

        # Verify committed
        row = db.query_one("SELECT * FROM messages WHERE text = ?", ("Test message",))
        assert row is not None

    def test_transaction_rollback_on_error(self, temp_db):
        try:
            with db.transaction() as conn:
                conn.execute(
                    "INSERT INTO messages (text, timestamp) VALUES (?, ?)",
                    ("Rollback test", "2024-01-01T00:00:00Z")
                )
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Verify rolled back
        row = db.query_one("SELECT * FROM messages WHERE text = ?", ("Rollback test",))
        assert row is None


class TestQueryHelpers:
    """Test query helper functions."""

    def test_query_one_found(self, populated_db):
        row = db.query_one("SELECT * FROM messages WHERE id = ?", (populated_db[0],))
        assert row is not None
        assert row['id'] == populated_db[0]

    def test_query_one_not_found(self, temp_db):
        row = db.query_one("SELECT * FROM messages WHERE id = ?", (99999,))
        assert row is None

    def test_query_all(self, populated_db):
        rows = db.query_all("SELECT * FROM messages")
        assert len(rows) == len(populated_db)


class TestInsertUpdate:
    """Test insert and update operations."""

    def test_insert_returns_id(self, temp_db):
        msg_id = db.insert('messages', {
            'text': 'Insert test',
            'timestamp': '2024-01-01T00:00:00Z',
        })
        assert msg_id is not None
        assert msg_id > 0

    def test_update_returns_count(self, populated_db):
        count = db.update(
            'messages',
            {'speaker': 'TOWER'},
            'id = ?',
            (populated_db[0],)
        )
        assert count == 1

    def test_update_multiple(self, populated_db):
        count = db.update(
            'messages',
            {'speaker': 'UNKNOWN'},
            '1 = 1',
            ()
        )
        assert count == len(populated_db)


class TestMessageHelpers:
    """Test message-specific helper functions."""

    def test_get_message(self, populated_db):
        msg = db.get_message(populated_db[0])
        assert msg is not None
        assert msg['id'] == populated_db[0]

    def test_get_messages_with_limit(self, populated_db):
        messages = db.get_messages(limit=2)
        assert len(messages) <= 2

    def test_get_messages_filter_by_speaker(self, populated_db):
        # First update some with speaker
        db.update('messages', {'speaker': 'TOWER'}, 'id = ?', (populated_db[0],))
        db.update('messages', {'speaker': 'AIRCRAFT'}, 'id = ?', (populated_db[1],))

        tower_msgs = db.get_messages(speaker='TOWER')
        for msg in tower_msgs:
            assert msg['speaker'] == 'TOWER'

    def test_save_message(self, temp_db):
        msg_id = db.save_message(
            text='Hello tower',
            timestamp='2024-01-01T12:00:00Z',
            callsign='TEST123',
            speaker='AIRCRAFT',
        )
        assert msg_id > 0

        msg = db.get_message(msg_id)
        assert msg['callsign'] == 'TEST123'
        assert msg['speaker'] == 'AIRCRAFT'

    def test_update_message_analysis(self, populated_db):
        count = db.update_message_analysis(
            populated_db[0],
            callsign='UPDATED123',
            speaker='TOWER',
        )
        assert count == 1

        msg = db.get_message(populated_db[0])
        assert msg['callsign'] == 'UPDATED123'
        assert msg['speaker'] == 'TOWER'
