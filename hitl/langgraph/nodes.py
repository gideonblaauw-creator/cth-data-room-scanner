"""LangGraph nodes — Context → proposal → HITL interrupt → locks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.types import interrupt

from hitl.langgraph.config import load_understanding_lab
from hitl.langgraph.findings import gate_findings, load_findings
from hitl.langgraph.locks import build_locks_document, locks_path_for_findings, save_locks
from hitl.langgraph.state import ReviewGraphState


def load_review_job(state: ReviewGraphState) -> dict[str, Any]:
    """Context node — load findings and attach Scanner Understanding Lab URLs."""
    path = Path(state["findings_path"])
    doc = load_findings(path)
    lab = load_understanding_lab()
    return {
        "findings_doc": doc,
        "understanding_lab": lab.as_dict(),
        "job_id": state.get("job_id") or doc.get("run_id", path.stem),
        "status": "loaded",
    }


def propose_suggestions(state: ReviewGraphState) -> dict[str, Any]:
    """Agent proposal — surface gate findings with existing agent suggestions."""
    pending = gate_findings(state["findings_doc"])
    proposals = [
        {
            "finding_id": f["finding_id"],
            "fixture_path": f.get("fixture_path") or f.get("source_path"),
            "pillar": f.get("pillar"),
            "label": f.get("label"),
            "agent_suggestion": f.get("agent_suggestion"),
            "rule_fired": f.get("rule_fired"),
            "excerpt_preview": (f.get("excerpt") or "")[:160],
        }
        for f in pending
    ]
    return {"pending": proposals, "status": "awaiting_human"}


def hitl_interrupt_gate(state: ReviewGraphState) -> dict[str, Any]:
    """
    Understanding Lab gate — pause for human agree / override / defer.

    Resume payload shape:
      {
        "decisions": [{"finding_id", "human_decision", "rationale", ...}],
        "quiz_passed": bool,
        "reviewer": str | null
      }
    """
    payload = interrupt(
        {
            "type": "understanding_lab_gate",
            "job_id": state.get("job_id"),
            "understanding_lab": state.get("understanding_lab", {}),
            "pending": state.get("pending", []),
            "instructions": (
                "Review each pending finding in the Understanding Lab loop "
                "(Context → Explanation → Playground → Shared decisions). "
                "Resume with agree, override, or defer per finding; rationale min 8 chars."
            ),
        }
    )
    if not isinstance(payload, dict) or "decisions" not in payload:
        raise ValueError("resume payload must include decisions[]")
    return {"human_payload": payload, "status": "human_resumed"}


def persist_locks(state: ReviewGraphState) -> dict[str, Any]:
    """Write locks compatible with microworld schema and /api/review/.../locks."""
    human = state["human_payload"]
    findings_path = Path(state["findings_path"])
    locks_doc = build_locks_document(
        state["findings_doc"],
        human["decisions"],
        quiz_passed=bool(human.get("quiz_passed", False)),
        reviewer=human.get("reviewer"),
        run_link=str(locks_path_for_findings(findings_path)),
    )
    out_path = save_locks(
        locks_doc,
        locks_path_for_findings(findings_path),
        job_id=state.get("job_id"),
    )
    return {
        "locks_doc": locks_doc,
        "locks_path": str(out_path),
        "status": "completed",
    }
