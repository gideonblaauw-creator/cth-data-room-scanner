"""Tests for scanner/crawl.py"""

import pytest

from scanner.config import BECAPS_CALIBRATION_FOLDER_ID
from scanner.crawl import (
    MAX_CONTENT_CHARS_PER_FILE,
    MAX_FILES_TO_READ_FULLY,
    PRIORITY_FILE_KEYWORDS,
    extract_folder_id,
    _priority_score,
    _mime_to_type,
)


class TestExtractFolderId:
    def test_full_url(self):
        url = "https://drive.google.com/drive/folders/1abcXYZ_123"
        assert extract_folder_id(url) == "1abcXYZ_123"

    def test_raw_id(self):
        assert extract_folder_id("1sg4TlFoP2_YVYmDdxuacC3Gs4kpB0Bd_") == "1sg4TlFoP2_YVYmDdxuacC3Gs4kpB0Bd_"

    def test_url_with_query(self):
        url = "https://drive.google.com/open?id=abc123def456"
        assert extract_folder_id(url) == "abc123def456"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            extract_folder_id("too short")


class TestPriorityScore:
    def test_pitch_deck_high_priority(self):
        assert _priority_score("Pitch Deck v3.pdf") > _priority_score("random.txt")

    def test_keyword_in_name(self):
        for kw in ["one-pager", "cap table", "financial"]:
            assert _priority_score(f"company_{kw}.pdf") > 0


class TestMimeToType:
    def test_folder(self):
        assert _mime_to_type("application/vnd.google-apps.folder", "x") == "folder"

    def test_pdf(self):
        assert _mime_to_type("application/pdf", "doc.pdf") == "pdf"


class TestConstants:
    def test_caps_match_schema(self):
        assert MAX_FILES_TO_READ_FULLY == 20
        assert MAX_CONTENT_CHARS_PER_FILE == 4000

    def test_becaps_is_calibration(self):
        assert BECAPS_CALIBRATION_FOLDER_ID.startswith("1sg4Tl")
