"""
Test Subtitle Processing
=========================
Testet die Verarbeitung von Untertiteln (SRT -> Text).
"""
import pytest
import sys
from pathlib import Path

# Import der zu testenden Funktionen
sys.path.insert(0, str(Path(__file__).parent.parent))
from run_youtube_history_scraper import clean_srt_to_text


def test_clean_srt_to_text_basic():
    """Testet grundlegende SRT-Bereinigung"""
    srt_input = """1
00:00:01,000 --> 00:00:03,000
Hello World

2
00:00:04,000 --> 00:00:06,000
This is a test
"""

    expected = "Hello World This is a test"
    result = clean_srt_to_text(srt_input)

    assert result == expected, f"Expected '{expected}', got '{result}'"


def test_clean_srt_to_text_removes_timestamps():
    """Testet ob Zeitstempel entfernt werden"""
    srt_input = """00:00:01,234 --> 00:00:05,678
Some subtitle text"""

    result = clean_srt_to_text(srt_input)

    assert "00:00" not in result, "Timestamps should be removed"
    assert "-->" not in result, "Timestamp arrows should be removed"
    assert "Some subtitle text" in result, "Actual text should be preserved"


def test_clean_srt_to_text_removes_numbers():
    """Testet ob SRT-Nummern entfernt werden"""
    srt_input = """1
Text one

2
Text two

3
Text three"""

    result = clean_srt_to_text(srt_input)

    # Zahlen sollten nicht am Anfang stehen
    assert not result.startswith("1"), "SRT numbers should be removed"
    assert not result.startswith("2"), "SRT numbers should be removed"
    assert not result.startswith("3"), "SRT numbers should be removed"

    # Text sollte erhalten bleiben
    assert "Text one" in result
    assert "Text two" in result
    assert "Text three" in result


def test_clean_srt_to_text_handles_empty_lines():
    """Testet Umgang mit Leerzeilen"""
    srt_input = """1
00:00:01,000 --> 00:00:02,000
First line


2
00:00:03,000 --> 00:00:04,000
Second line

"""

    result = clean_srt_to_text(srt_input)

    # Keine mehrfachen Leerzeichen
    assert "  " not in result, "No double spaces should exist"

    # Text sollte mit Leerzeichen verbunden sein
    assert "First line Second line" == result


def test_clean_srt_to_text_empty_input():
    """Testet leere Eingabe"""
    result = clean_srt_to_text("")
    assert result == "", "Empty input should return empty string"


def test_clean_srt_to_text_preserves_german_umlauts():
    """Testet ob deutsche Umlaute erhalten bleiben"""
    srt_input = """1
00:00:01,000 --> 00:00:02,000
Über äöü ÄÖÜ ß
"""

    result = clean_srt_to_text(srt_input)

    assert "Über" in result
    assert "äöü" in result
    assert "ÄÖÜ" in result
    assert "ß" in result
