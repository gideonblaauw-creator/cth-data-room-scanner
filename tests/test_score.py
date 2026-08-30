"""Tests for scanner/score.py and score_runner.py"""

import json

from scanner.score import (
    PILLAR_ORDER,
    SCORING_OUTPUT_SCHEMA,
    score_to_status,
    THRESHOLDS,
)
from scanner.score_runner import load_becaps_fixture, _normalize_scoring


class TestScoreToStatus:
    def test_strong(self):
        assert score_to_status(4.5) == "strong"

    def test_emerging(self):
        assert score_to_status(3.7) == "emerging"

    def test_developing(self):
        assert score_to_status(3.2) == "developing"

    def test_needs_work(self):
        assert score_to_status(1.5) == "needs_work"


class TestBecapsFixture:
    def test_loads(self):
        data = load_becaps_fixture()
        assert data["company"]["name"] == "BeCaps"
        assert data["overall"]["score"] == 3.5
        assert data["overall"]["recommendation"] == "go_phase1"

    def test_all_pillars_present(self):
        data = load_becaps_fixture()
        for pid in PILLAR_ORDER:
            assert pid in data["pillars"]
            assert "score" in data["pillars"][pid]

    def test_becaps_calibration_folder_readonly(self):
        data = load_becaps_fixture()
        assert data["company"]["drive_folder_id"] == "1sg4TlFoP2_YVYmDdxuacC3Gs4kpB0Bd_"


class TestNormalizeScoring:
    def test_fills_missing_pillars(self):
        raw = {"company": {}, "overall": {}, "pillars": {}}
        result = _normalize_scoring(raw, "TestCo", "es", "2026-08-30", "folder123")
        assert len(result["pillars"]) == 8
        assert result["company"]["name"] == "TestCo"

    def test_recomputes_overall(self):
        raw = {
            "company": {},
            "overall": {},
            "pillars": {pid: {"score": 4.0} for pid in PILLAR_ORDER},
        }
        result = _normalize_scoring(raw, "X", "es", "2026-08-30", "f")
        assert result["overall"]["score"] == 4.0
        assert result["overall"]["recommendation"] == "go_phase1"
