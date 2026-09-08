"""
scanner/fixture_scan.py
Local fixture scanner for HITL dry runs — no Drive API, no LLM, no secrets.

Reads fixtures/sample-dataroom/ and applies deterministic rule checks to emit
structured findings for human-in-the-loop review workflows.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURE_DIR = REPO_ROOT / "fixtures" / "sample-dataroom"

# Deterministic rules: (pattern, rule_id, label, action, reason_template)
RULES: list[tuple[re.Pattern[str], str, str, str, str]] = [
    (
        re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]", re.MULTILINE),
        "R001",
        "needs_human",
        "redact_or_escalate",
        "Possible credential pattern detected",
    ),
    (
        re.compile(r"(?i)IBAN:\s*NL\*\*", re.MULTILINE),
        "R002",
        "needs_human",
        "confirm_redaction",
        "Partial bank account number visible",
    ),
    (
        re.compile(r"(?i)(needs_human|human review required|human should)", re.MULTILINE),
        "R003",
        "needs_human",
        "manual_review",
        "Document self-flags for human review",
    ),
    (
        re.compile(r"(?i)(unsigned|non-binding|ambiguous|unclear)", re.MULTILINE),
        "R004",
        "unclear",
        "legal_review",
        "Ambiguous legal or binding language",
    ),
    (
        re.compile(r"(?i)(SAFE|cap table|ownership|%|dilution)", re.MULTILINE),
        "R005",
        "unclear",
        "verify_cap_table",
        "Cap table or dilution signals need verification",
    ),
    (
        re.compile(r"(?i)(projected|draft|not audited|placeholder)", re.MULTILINE),
        "R006",
        "needs_human",
        "verify_financials",
        "Unaudited or projected financial figures",
    ),
    (
        re.compile(r"(?i)(patent|EP20|NL20|MIT license|public)", re.MULTILINE),
        "R007",
        "auto_ok",
        "include_in_report",
        "Public or standard disclosure content",
    ),
    (
        re.compile(r"(?i)(mission|team|linkedin|founded|sector)", re.MULTILINE),
        "R008",
        "auto_ok",
        "include_in_report",
        "Standard company overview content",
    ),
]

LABEL_PRIORITY = {"needs_human": 3, "unclear": 2, "auto_ok": 1}


@dataclass
class ReasoningStep:
    step: int
    rule_id: str
    description: str
    matched_text: str | None = None


@dataclass
class Finding:
    finding_id: str
    fixture_path: str
    pillar: str
    label: str
    expected_label: str
    agent_suggestion: str
    rule_fired: str
    reasoning_steps: list[ReasoningStep] = field(default_factory=list)
    excerpt: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["reasoning_steps"] = [asdict(s) for s in self.reasoning_steps]
        return d


@dataclass
class ScanOutput:
    run_id: str
    scanned_at: str
    company: str
    dataroom_id: str
    fixture_root: str
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "scanned_at": self.scanned_at,
            "company": self.company,
            "dataroom_id": self.dataroom_id,
            "fixture_root": self.fixture_root,
            "findings": [f.to_dict() for f in self.findings],
            "summary": {
                "total": len(self.findings),
                "auto_ok": sum(1 for f in self.findings if f.label == "auto_ok"),
                "needs_human": sum(1 for f in self.findings if f.label == "needs_human"),
                "unclear": sum(1 for f in self.findings if f.label == "unclear"),
            },
        }


def load_manifest(fixture_dir: Path | None = None) -> dict[str, Any]:
    root = fixture_dir or DEFAULT_FIXTURE_DIR
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _best_label_and_steps(content: str) -> tuple[str, str, str, list[ReasoningStep]]:
    """Apply rules and return (label, rule_id, action, reasoning_steps)."""
    matches: list[tuple[str, str, str, str, str | None]] = []
    for pattern, rule_id, label, action, reason in RULES:
        m = pattern.search(content)
        if m:
            snippet = m.group(0)[:120]
            matches.append((label, rule_id, action, reason, snippet))

    if not matches:
        return "auto_ok", "R000", "include_in_report", [
            ReasoningStep(1, "R000", "No risk rules matched", None)
        ]

    # Highest-priority label wins
    best = max(matches, key=lambda x: LABEL_PRIORITY.get(x[0], 0))
    label, rule_id, action, reason, snippet = best

    steps = [
        ReasoningStep(i + 1, rid, rsn, snip)
        for i, (_, rid, _, rsn, snip) in enumerate(matches[:5])
    ]
    return label, rule_id, action, steps


def scan_fixtures(fixture_dir: Path | None = None, run_id: str | None = None) -> ScanOutput:
    """Scan local fixture dataroom and return structured findings."""
    root = (fixture_dir or DEFAULT_FIXTURE_DIR).resolve()
    manifest = load_manifest(root)
    now = datetime.now(timezone.utc).isoformat()
    rid = run_id or f"hitl-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    findings: list[Finding] = []
    for i, entry in enumerate(manifest.get("files", []), start=1):
        rel_path = entry["path"]
        file_path = root / rel_path
        if not file_path.exists():
            findings.append(
                Finding(
                    finding_id=f"F{i:03d}",
                    fixture_path=rel_path,
                    pillar=entry.get("pillar", "unknown"),
                    label="unclear",
                    expected_label=entry.get("expected_label", "unclear"),
                    agent_suggestion="missing_file",
                    rule_fired="R_MISSING",
                    reasoning_steps=[
                        ReasoningStep(1, "R_MISSING", f"Fixture file not found: {rel_path}")
                    ],
                )
            )
            continue

        content = file_path.read_text(encoding="utf-8", errors="replace")
        label, rule_id, action, steps = _best_label_and_steps(content)
        excerpt = content[:400].replace("\n", " ").strip()

        findings.append(
            Finding(
                finding_id=f"F{i:03d}",
                fixture_path=rel_path,
                pillar=entry.get("pillar", "unknown"),
                label=label,
                expected_label=entry.get("expected_label", "unclear"),
                agent_suggestion=action,
                rule_fired=rule_id,
                reasoning_steps=steps,
                excerpt=excerpt,
            )
        )

    return ScanOutput(
        run_id=rid,
        scanned_at=now,
        company=manifest.get("company", "Unknown"),
        dataroom_id=manifest.get("dataroom_id", "unknown"),
        fixture_root=str(root),
        findings=findings,
    )
