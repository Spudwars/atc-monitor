"""Tests for callsign extraction."""

import pytest
from processor.callsign import (
    CallsignExtractor,
    extract_callsign,
    PHONETIC_ALPHABET,
    PHONETIC_NUMBERS,
)


class TestPhoneticNormalization:
    """Test phonetic alphabet and number conversion."""

    def test_phonetic_alphabet(self):
        extractor = CallsignExtractor()
        result = extractor.normalize_phonetic("Alpha Bravo Charlie")
        assert result == "A B C"

    def test_phonetic_numbers(self):
        extractor = CallsignExtractor()
        result = extractor.normalize_phonetic("One Two Three")
        assert result == "1 2 3"

    def test_mixed_phonetic(self):
        extractor = CallsignExtractor()
        result = extractor.normalize_phonetic("November One Two Three Alpha Bravo")
        assert result == "N 1 2 3 A B"

    def test_niner_for_nine(self):
        extractor = CallsignExtractor()
        result = extractor.normalize_phonetic("Niner")
        assert result == "9"


class TestAirlineCallsigns:
    """Test airline callsign extraction."""

    def test_speedbird(self):
        result = extract_callsign("Speedbird 123 descend flight level 280")
        assert result == "SPEEDBIRD 123"

    def test_ryanair(self):
        result = extract_callsign("Ryanair 456 cleared to land")
        assert result == "RYANAIR 456"

    def test_callsign_with_spaces(self):
        result = extract_callsign("Speedbird 1 2 3 roger")
        assert result == "SPEEDBIRD 123"

    def test_no_callsign(self):
        result = extract_callsign("Say again please")
        assert result is None


class TestRegistrations:
    """Test aircraft registration extraction."""

    def test_us_registration(self):
        result = extract_callsign("N12345 taxiing to runway")
        assert result == "N12345"

    def test_us_registration_with_letters(self):
        result = extract_callsign("N123AB requesting clearance")
        assert result == "N123AB"

    def test_uk_registration(self):
        result = extract_callsign("Golf Alpha Bravo Charlie Delta ready for departure")
        # After phonetic normalization: G A B C D
        # Should match G-ABCD pattern
        extractor = CallsignExtractor()
        matches = extractor.extract_all("G-ABCD ready for departure")
        assert len(matches) == 1
        assert matches[0].callsign == "G-ABCD"


class TestICAOCodes:
    """Test ICAO 3-letter code extraction."""

    def test_icao_format(self):
        extractor = CallsignExtractor()
        matches = extractor.extract_all("BAW123 contact approach")
        assert len(matches) >= 1
        icao_match = next((m for m in matches if m.icao == "BAW"), None)
        assert icao_match is not None
        assert icao_match.callsign == "BAW123"


class TestExtractorWithDatabase:
    """Test callsign extraction with operator database."""

    def test_operator_lookup(self):
        extractor = CallsignExtractor()
        extractor._callsign_db = {
            'SPEEDBIRD': ('British Airways', 'BAW'),
            'RYANAIR': ('Ryanair', 'RYR'),
        }

        matches = extractor.extract_all("Speedbird 123 descend")
        assert len(matches) == 1
        assert matches[0].callsign == "SPEEDBIRD 123"
        assert matches[0].operator == "British Airways"
        assert matches[0].icao == "BAW"


class TestConfidenceScoring:
    """Test confidence scoring for different match types."""

    def test_registration_high_confidence(self):
        extractor = CallsignExtractor()
        matches = extractor.extract_all("N12345 taxi")
        assert matches[0].confidence >= 0.9

    def test_known_airline_higher_confidence(self):
        extractor = CallsignExtractor()
        extractor._callsign_db = {'SPEEDBIRD': ('British Airways', 'BAW')}

        known = extractor.extract_all("Speedbird 123")
        unknown = extractor.extract_all("Foobar 123")

        assert known[0].confidence > unknown[0].confidence
