"""Unit tests for score → findings adapter and production review routes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scanner.findings_from_score import (
    findings_from_score,
    load_findings,
    normalize_findings_doc,
    save_findings,
)
from scanner.score_runner import load_becaps_fixture

BECAPS_FIXTURE = ROOT / "fixtures" / "becaps_scoring.json"
FIXTURE_FINDINGS = ROOT / "hitl" / "microworld" / "defaults" / "findings-hitl-20260908-214515.json"
LOCKS_SCHEMA = ROOT / "hitl" / "microworld" / "schema" / "microworld-locks.schema.json"


class TestFindingsFromScore:
    def test_becaps_produces_findings_with_labels(self):
        scoring = load_becaps_fixture()
        doc = findings_from_score(scoring, source="dry_run", run_id="test-run")

        assert doc["run_id"] == "test-run"
        assert doc["source"] == "dry_run"
        assert doc["company"] == "BeCaps"
        assert len(doc["findings"]) >= 10

        labels = {f["label"] for f in doc["findings"]}
        assert "needs_human" in labels or "unclear" in labels

        for f in doc["findings"]:
            assert f["finding_id"].startswith("S")
            assert f["source_path"]
            assert f["pillar"]
            assert f["rule_fired"]
            assert f["agent_suggestion"]
            assert len(f["reasoning_steps"]) >= 1

    def test_eligibility_warn_becomes_finding(self):
        scoring = load_becaps_fixture()
        doc = findings_from_score(scoring, source="dry_run")
        eligibility = [f for f in doc["findings"] if f["pillar"] == "eligibility"]
        assert len(eligibility) >= 1
        assert eligibility[0]["rule_fired"] == "eligibility_warn"
        assert eligibility[0]["label"] == "unclear"

    def test_stable_sequential_ids(self):
        scoring = load_becaps_fixture()
        doc = findings_from_score(scoring, source="dry_run")
        ids = [f["finding_id"] for f in doc["findings"]]
        assert ids[0] == "S001"
        assert ids == [f"S{i:03d}" for i in range(1, len(ids) + 1)]

    def test_save_and_load_round_trip(self, tmp_path):
        scoring = load_becaps_fixture()
        doc = findings_from_score(scoring, source="live_scan", run_id="round-trip")
        path = tmp_path / "test.findings.json"
        save_findings(doc, path)
        loaded = load_findings(path)
        assert loaded["run_id"] == "round-trip"
        assert len(loaded["findings"]) == len(doc["findings"])


class TestNormalizeFindings:
    def test_fixture_microworld_shape(self):
        raw = json.loads(FIXTURE_FINDINGS.read_text())
        doc = normalize_findings_doc(raw)
        assert len(doc["findings"]) >= 5
        for f in doc["findings"]:
            assert "source_path" in f
            assert f["finding_id"].startswith("F")

    def test_gate_findings_alias(self):
        raw = {"run_id": "x", "company": "Co", "gate_findings": [
            {"finding_id": "F001", "fixture_path": "a.md", "label": "auto_ok",
             "agent_suggestion": "ok", "rule_fired": "R001", "excerpt": "x"}
        ]}
        doc = normalize_findings_doc(raw)
        assert doc["findings"][0]["source_path"] == "a.md"


class TestReviewLocksRoundTrip:
    def _sample_production_locks(self, findings_doc: dict) -> dict:
        locks = []
        for f in findings_doc["findings"][:3]:
            locks.append({
                "finding_id": f["finding_id"],
                "fixture_path": f["source_path"],
                "agent_suggestion": f["agent_suggestion"],
                "agent_label": f["label"],
                "human_decision": "agree",
                "rationale": "Confirmed after diligence review.",
                "status": "reviewed",
                "locked_at": "2026-09-12T14:00:00+00:00",
            })
        return {
            "version": 1,
            "run_id": findings_doc["run_id"],
            "company": findings_doc["company"],
            "quiz_passed": True,
            "locked_at": "2026-09-12T14:00:00+00:00",
            "locks": locks,
        }

    def test_locks_compatible_with_microworld_schema_fields(self):
        scoring = load_becaps_fixture()
        doc = findings_from_score(scoring, source="dry_run")
        locks = self._sample_production_locks(doc)
        schema = json.loads(LOCKS_SCHEMA.read_text())
        required_top = schema["required"]
        for key in required_top:
            if key == "quiz_passed":
                assert isinstance(locks[key], bool)
            else:
                assert key in locks
        lock_def = schema["$defs"]["lock"]["required"]
        for lock in locks["locks"]:
            for key in lock_def:
                assert key in lock
            assert lock["human_decision"] in {"agree", "override", "defer"}
            assert len(lock["rationale"]) >= 8

    def test_s_prefixed_finding_ids_in_locks(self):
        scoring = load_becaps_fixture()
        doc = findings_from_score(scoring, source="dry_run")
        locks = self._sample_production_locks(doc)
        for lock in locks["locks"]:
            assert lock["finding_id"].startswith("S")


class TestReviewFlaskRoutes:
    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
        from app.main import app

        app.config["TESTING"] = True
        return app.test_client()

    def test_review_page_serves_html(self, client):
        res = client.get("/review/demo")
        assert res.status_code == 200
        assert b"CTH Production Reviewer" in res.data

    def test_api_findings_becaps_alias(self, client, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
        res = client.get("/api/review/becaps/findings")
        assert res.status_code == 200
        data = res.get_json()
        assert data["company"]
        assert len(data["findings"]) >= 1

    def test_api_save_locks(self, client, tmp_path, monkeypatch):
        monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
        # Ensure becaps findings exist
        client.get("/api/review/becaps/findings")
        scoring = load_becaps_fixture()
        doc = findings_from_score(scoring, source="dry_run", run_id="becaps-demo")
        path = tmp_path / "becaps-demo-2026-04.findings.json"
        save_findings(doc, path)

        locks = {
            "version": 1,
            "run_id": doc["run_id"],
            "company": doc["company"],
            "quiz_passed": True,
            "locked_at": "2026-09-12T14:00:00+00:00",
            "locks": [{
                "finding_id": doc["findings"][0]["finding_id"],
                "fixture_path": doc["findings"][0]["source_path"],
                "agent_suggestion": doc["findings"][0]["agent_suggestion"],
                "agent_label": doc["findings"][0]["label"],
                "human_decision": "agree",
                "rationale": "Reviewed and confirmed for audit trail.",
                "status": "reviewed",
                "locked_at": "2026-09-12T14:00:01+00:00",
            }],
        }
        res = client.post(
            f"/api/review/becaps/locks?path={path}",
            json=locks,
            content_type="application/json",
        )
        assert res.status_code == 200
        assert res.get_json()["ok"] is True

    def test_health_still_works(self, client):
        res = client.get("/health")
        assert res.status_code == 200
