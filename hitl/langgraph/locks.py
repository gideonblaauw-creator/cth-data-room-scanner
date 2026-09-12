"""
Build and persist review locks compatible with microworld schema and
`/api/review/<job_id>/locks` (production reviewer branch).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_DECISIONS = {"agree", "override", "defer"}
VALID_STATUSES = {"pending", "reviewed", "waived", "blocked"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def locks_path_for_findings(findings_path: Path) -> Path:
    """Mirror app/review.py naming: `{stem}-review-locks.json`."""
    return findings_path.with_name(findings_path.stem + "-review-locks.json")


def build_locks_document(
    findings_doc: dict[str, Any],
    decisions: list[dict[str, Any]],
    *,
    quiz_passed: bool = False,
    reviewer: str | None = None,
    run_link: str | None = None,
) -> dict[str, Any]:
    by_id = {d["finding_id"]: d for d in decisions}
    locks: list[dict[str, Any]] = []
    locked_at = _now_iso()

    for finding in findings_doc.get("findings", []):
        fid = finding["finding_id"]
        if fid not in by_id:
            continue
        decision = by_id[fid]
        human = decision["human_decision"]
        if human not in VALID_DECISIONS:
            raise ValueError(f"invalid human_decision for {fid}: {human}")
        rationale = decision.get("rationale", "")
        if len(rationale) < 8:
            raise ValueError(f"rationale too short for {fid} (min 8 chars)")

        locks.append(
            {
                "finding_id": fid,
                "fixture_path": finding.get("fixture_path") or finding.get("source_path", ""),
                "agent_suggestion": finding.get("agent_suggestion", "review_item"),
                "agent_label": finding.get("label"),
                "human_decision": human,
                "rationale": rationale,
                "status": decision.get("status", "reviewed"),
                "locked_at": decision.get("locked_at", locked_at),
                "moment": finding.get("moment"),
            }
        )

    if not locks:
        raise ValueError("decisions did not match any findings")

    return {
        "version": 1,
        "run_id": findings_doc.get("run_id", "unknown"),
        "company": findings_doc.get("company", "Unknown"),
        "quiz_passed": quiz_passed,
        "locked_at": locked_at,
        "reviewer": reviewer,
        "run_link": run_link,
        "locks": locks,
    }


def save_locks(locks_doc: dict[str, Any], path: Path, *, job_id: str | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(locks_doc)
    payload.setdefault("saved_at", _now_iso())
    if job_id:
        payload.setdefault("job_id", job_id)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
