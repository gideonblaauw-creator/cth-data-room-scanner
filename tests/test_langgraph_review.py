"""LangGraph HITL dogfood — compile + interrupt/resume smoke tests."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

pytest.importorskip("langgraph")

from langgraph.types import Command

from hitl.langgraph.config import load_understanding_lab
from hitl.langgraph.findings import default_fixture_path, gate_findings, load_findings
from hitl.langgraph.graph import build_review_graph, compile_review_graph
from hitl.langgraph.locks import build_locks_document, locks_path_for_findings

FIXTURE = default_fixture_path(ROOT)
DECISIONS_EXAMPLE = ROOT / "hitl" / "langgraph" / "fixtures" / "langgraph-decisions.example.json"
LOCKS_SCHEMA = ROOT / "hitl" / "microworld" / "schema" / "microworld-locks.schema.json"


class TestLangGraphCompile:
    def test_graph_builds_and_compiles(self):
        builder = build_review_graph()
        assert "load_review_job" in builder.nodes
        graph = compile_review_graph()
        assert graph is not None

    def test_no_secrets_in_config_module(self):
        import hitl.langgraph.config as cfg

        source = Path(cfg.__file__).read_text(encoding="utf-8").lower()
        assert "sk-" not in source
        assert "api_key=" not in source
        assert "password" not in source


class TestFindingsLoader:
    def test_loads_microworld_fixture(self):
        doc = load_findings(FIXTURE)
        assert doc["company"] == "VertiGreen Robotics"
        assert len(doc["findings"]) >= 5
        gated = gate_findings(doc)
        assert all(f["label"] in {"needs_human", "unclear"} for f in gated)
        assert len(gated) >= 1


class TestUnderstandingLabUrls:
    def test_ticket_lab_notion_urls(self):
        lab = load_understanding_lab()
        assert "3d5dfee50be98174a045febce0fc4b3d" in lab.context_url
        assert "3d9dfee50be981ab8bd4ff5fd40c8e35" in lab.playground_url
        assert "bb52cfa45b6744e59983528480fbab4b" in lab.shared_decisions_url


class TestInterruptResumeSmoke:
    def test_interrupt_then_resume_writes_locks(self, tmp_path):
        findings_copy = tmp_path / "findings.json"
        findings_copy.write_text(FIXTURE.read_text(encoding="utf-8"))

        graph = compile_review_graph()
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        interrupted = False
        interrupt_payload = None
        for chunk in graph.stream(
            {"job_id": "test-hitl", "findings_path": str(findings_copy)},
            config,
            stream_mode="updates",
        ):
            if "__interrupt__" in chunk:
                interrupted = True
                interrupt_payload = chunk["__interrupt__"][0].value
                break

        assert interrupted is True
        assert interrupt_payload["type"] == "understanding_lab_gate"
        assert "understanding_lab" in interrupt_payload
        assert interrupt_payload["understanding_lab"]["context"]
        assert len(interrupt_payload["pending"]) >= 1

        resume = {
            "decisions": [
                {
                    "finding_id": interrupt_payload["pending"][0]["finding_id"],
                    "human_decision": "agree",
                    "rationale": "Smoke test — confirmed after Understanding Lab review.",
                    "status": "reviewed",
                }
            ],
            "quiz_passed": True,
            "reviewer": "pytest",
        }
        final = graph.invoke(Command(resume=resume), config)
        assert final["status"] == "completed"
        locks_path = Path(final["locks_path"])
        assert locks_path.exists()
        locks = json.loads(locks_path.read_text())
        assert locks["version"] == 1
        assert len(locks["locks"]) == 1

    def test_locks_compatible_with_microworld_schema(self):
        doc = load_findings(FIXTURE)
        gated = gate_findings(doc)[:2]
        decisions = [
            {
                "finding_id": f["finding_id"],
                "human_decision": "agree",
                "rationale": "Schema compatibility check for locks export.",
                "status": "reviewed",
            }
            for f in gated
        ]
        locks = build_locks_document(doc, decisions, quiz_passed=True)
        schema = json.loads(LOCKS_SCHEMA.read_text())
        for key in schema["required"]:
            assert key in locks
        lock_req = schema["$defs"]["lock"]["required"]
        for lock in locks["locks"]:
            for key in lock_req:
                assert key in lock

    def test_locks_path_matches_review_api_convention(self, tmp_path):
        findings = tmp_path / "becaps-demo-2026-04.findings.json"
        expected = tmp_path / "becaps-demo-2026-04.findings-review-locks.json"
        assert locks_path_for_findings(findings) == expected
