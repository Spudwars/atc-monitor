"""Tests for post-processing module."""

import pytest
from processor.postprocess import detect_speaker, analyze_message, reanalyze_messages
from processor import db


class TestSpeakerDetection:
    """Test speaker role detection."""

    def test_tower_instruction_descend(self):
        assert detect_speaker("Speedbird 123 descend flight level 280") == "TOWER"

    def test_tower_instruction_cleared(self):
        assert detect_speaker("Ryanair 456 cleared to land runway 27") == "TOWER"

    def test_tower_instruction_hold_short(self):
        assert detect_speaker("Hold short runway 09") == "TOWER"

    def test_aircraft_readback_wilco(self):
        assert detect_speaker("Wilco Speedbird 123") == "AIRCRAFT"

    def test_aircraft_readback_roger(self):
        assert detect_speaker("Roger descending 280") == "AIRCRAFT"

    def test_aircraft_request(self):
        assert detect_speaker("Requesting direct to waypoint") == "AIRCRAFT"

    def test_aircraft_position_report(self):
        assert detect_speaker("Established on final runway 27") == "AIRCRAFT"

    def test_ambiguous_defaults_to_aircraft(self):
        # No clear indicators
        assert detect_speaker("Speedbird 123") == "AIRCRAFT"

    def test_mixed_signals_higher_score_wins(self):
        # More tower indicators
        text = "Speedbird 123 descend maintain flight level 280 reduce speed"
        assert detect_speaker(text) == "TOWER"


class TestMessageAnalysis:
    """Test full message analysis."""

    def test_analyze_tower_message(self, fresh_cache):
        result = analyze_message(1, "Speedbird 123 descend flight level 280")
        assert result['speaker'] == "TOWER"
        assert result['callsign'] == "SPEEDBIRD 123"

    def test_analyze_aircraft_message(self, fresh_cache):
        result = analyze_message(2, "Roger Speedbird 123 descending 280")
        assert result['speaker'] == "AIRCRAFT"
        assert result['callsign'] == "SPEEDBIRD 123"

    def test_analyze_no_callsign(self, fresh_cache):
        result = analyze_message(3, "Say again please")
        assert result['speaker'] == "AIRCRAFT"
        assert result['callsign'] is None


class TestReanalyze:
    """Test bulk reanalysis."""

    def test_reanalyze_updates_messages(self, populated_db, fresh_cache):
        count = reanalyze_messages()
        assert count == len(populated_db)

        # Verify updates were applied
        messages = db.get_messages()
        for msg in messages:
            # Each message should have a speaker set
            assert msg['speaker'] in ('TOWER', 'AIRCRAFT')
