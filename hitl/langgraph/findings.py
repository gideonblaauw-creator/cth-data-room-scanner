"""
Load and normalize review findings for the LangGraph dogfood graph.

Reuses existing fixture / BeCaps / hitl-demo shapes without forking the reviewer UI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


GATE_LABELS = {"needs_human", "unclear"}


def normalize_findings_doc(raw: dict[str, Any]) -> dict[str, Any]:
    """Unify microworld gate_findings and standard findings arrays."""
    doc = dict(raw)
    findings = doc.get("findings") or doc.get("gate_findings") or []
    normalized: list[dict[str, Any]] = []
    for item in findings:
        f = dict(item)
        if "source_path" not in f and "fixture_path" in f:
            f["source_path"] = f["fixture_path"]
        if "fixture_path" not in f and "source_path" in f:
            f["fixture_path"] = f["source_path"]
        normalized.append(f)
    doc["findings"] = normalized
    return doc


def load_findings(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return normalize_findings_doc(raw)


def gate_findings(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Findings that need human review in the Understanding Lab loop."""
    return [f for f in doc.get("findings", []) if f.get("label") in GATE_LABELS]


def default_fixture_path(repo_root: Path) -> Path:
    return repo_root / "hitl" / "microworld" / "defaults" / "findings-hitl-20260908-214515.json"
