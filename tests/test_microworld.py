"""Tests for microworld lock JSON schema and Notion push script."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "hitl" / "microworld" / "schema" / "microworld-locks.schema.json"
DEFAULTS_PATH = (
    ROOT / "hitl" / "microworld" / "defaults" / "findings-hitl-20260908-214515.json"
)
PUSH_SCRIPT = ROOT / "hitl" / "scripts" / "push_microworld_to_notion.py"
EXAMPLE_QUIZ = ROOT / "hitl" / "microworld" / "quiz-answers.example.json"


def _sample_locks() -> dict:
    return {
        "version": 1,
        "run_id": "hitl-20260908-214515",
        "company": "VertiGreen Robotics",
        "quiz_passed": True,
        "quiz_source": "explainer-quiz",
        "locked_at": "2026-09-12T14:00:00+00:00",
        "reviewer": None,
        "run_link": "hitl/out/microworld-locks.json",
        "locks": [
            {
                "finding_id": "F004",
                "fixture_path": "financials-summary.md",
                "agent_suggestion": "manual_review",
                "agent_label": "needs_human",
                "human_decision": "agree",
                "rationale": "Draft financials flagged correctly; keep in diligence pack.",
                "status": "reviewed",
                "locked_at": "2026-09-12T14:00:01+00:00",
                "moment": "unaudited_financials",
            },
            {
                "finding_id": "F005",
                "fixture_path": "fake-invoice-redacted.txt",
                "agent_suggestion": "confirm_redaction",
                "agent_label": "needs_human",
                "human_decision": "override",
                "rationale": "Partial IBAN visible — redact fully before LP share.",
                "status": "reviewed",
                "locked_at": "2026-09-12T14:00:02+00:00",
                "moment": "iban_redaction",
            },
        ],
    }


class TestMicroworldDefaults:
    def test_defaults_file_exists_with_gate_findings(self):
        assert DEFAULTS_PATH.exists()
        data = json.loads(DEFAULTS_PATH.read_text())
        assert data["run_id"] == "hitl-20260908-214515"
        assert len(data["gate_findings"]) <= 10
        assert len(data["gate_findings"]) >= 5
        moments = {f.get("moment") for f in data["gate_findings"]}
        assert "iban_redaction" in moments
        assert "unaudited_financials" in moments
        assert "safe_cap_table" in moments
        assert "hallucinated_metric" in moments

    def test_quiz_example_has_required_fields(self):
        quiz = json.loads(EXAMPLE_QUIZ.read_text())
        assert quiz["version"] == 1
        assert "quiz_passed" in quiz
        assert len(quiz["answers"]) == 5


class TestMicroworldLockSchema:
    def test_schema_file_valid_json(self):
        schema = json.loads(SCHEMA_PATH.read_text())
        assert schema["title"] == "MicroworldLocks"
        assert schema["properties"]["version"]["const"] == 1

    def test_sample_locks_has_required_fields(self):
        locks = _sample_locks()
        for key in ("version", "run_id", "company", "quiz_passed", "locked_at", "locks"):
            assert key in locks
        for lock in locks["locks"]:
            assert lock["human_decision"] in {"agree", "override", "defer"}
            assert len(lock["rationale"]) >= 8

    def _load_push_module(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "push_microworld_to_notion", PUSH_SCRIPT
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    def test_invalid_decision_rejected_by_push_script(self, tmp_path):
        locks = _sample_locks()
        locks["locks"][0]["human_decision"] = "bulk_approve"
        path = tmp_path / "bad-locks.json"
        path.write_text(json.dumps(locks))

        mod = self._load_push_module()
        with pytest.raises(ValueError, match="Invalid human_decision"):
            mod.load_locks(path)

    def test_short_rationale_rejected(self, tmp_path):
        locks = _sample_locks()
        locks["locks"][0]["rationale"] = "short"
        path = tmp_path / "short.json"
        path.write_text(json.dumps(locks))

        mod = self._load_push_module()
        with pytest.raises(ValueError, match="Rationale too short"):
            mod.load_locks(path)


class TestPushMicroworldToNotion:
    def test_dry_run_validates_locks(self, tmp_path):
        path = tmp_path / "microworld-locks.json"
        path.write_text(json.dumps(_sample_locks()))

        proc = subprocess.run(
            [sys.executable, str(PUSH_SCRIPT), "--locks", str(path), "--dry-run"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert "[dry-run] upsert F004" in proc.stdout
        assert "[dry-run] upsert F005" in proc.stdout

    def test_paste_pack_offline(self, tmp_path):
        path = tmp_path / "microworld-locks.json"
        path.write_text(json.dumps(_sample_locks()))

        proc = subprocess.run(
            [sys.executable, str(PUSH_SCRIPT), "--locks", str(path), "--paste-pack"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0
        assert "F004" in proc.stdout
        assert "bb52cfa45b6744e59983528480fbab4b" in proc.stdout

    def test_missing_token_without_dry_run_fails(self, tmp_path, monkeypatch):
        path = tmp_path / "microworld-locks.json"
        path.write_text(json.dumps(_sample_locks()))
        monkeypatch.delenv("NOTION_API_TOKEN", raising=False)
        monkeypatch.delenv("NOTION_TOKEN", raising=False)

        proc = subprocess.run(
            [sys.executable, str(PUSH_SCRIPT), "--locks", str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 1
        assert "NOTION_API_TOKEN" in proc.stderr
