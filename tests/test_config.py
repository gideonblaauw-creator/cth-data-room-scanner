"""Tests for scanner/config.py and upload guards"""

import pytest

from scanner.config import (
    BECAPS_CALIBRATION_FOLDER_ID,
    DEFAULT_REPORTS_FOLDER_ID,
    assert_not_becaps_folder,
)


class TestBecapsGuard:
    def test_blocks_becaps_write(self):
        with pytest.raises(PermissionError, match="read-only"):
            assert_not_becaps_folder(BECAPS_CALIBRATION_FOLDER_ID, "upload")

    def test_allows_reports_folder(self):
        assert_not_becaps_folder(DEFAULT_REPORTS_FOLDER_ID, "upload")

    def test_allows_other_folders(self):
        assert_not_becaps_folder("some-other-folder-id", "upload")
