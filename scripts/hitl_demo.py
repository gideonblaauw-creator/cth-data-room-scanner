#!/usr/bin/env python3
"""
scripts/hitl_demo.py
HITL dry-run: scan synthetic fixtures, emit findings + Notion-ready templates.

No Drive API, no LLM, no live Notion auth required.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scanner.fixture_scan import ScanOutput, scan_fixtures

DEFAULT_OUT = ROOT / "out"
FIXTURE_DIR = ROOT / "fixtures" / "sample-dataroom"

QUIZ_QUESTIONS = [
    {
        "id": "Q1",
        "question": "Why does `fake-invoice-redacted.txt` receive `needs_human` instead of `auto_ok`?",
        "options": [
            "It contains a partial IBAN that may need redaction confirmation",
            "It is written in Dutch",
            "It has no date field",
            "It references a patent number",
        ],
        "answer": 0,
    },
    {
        "id": "Q2",
        "question": "What label should ambiguous cap-table / SAFE language typically get?",
        "options": ["auto_ok", "needs_human", "unclear", "skip"],
        "answer": 2,
    },
    {
        "id": "Q3",
        "question": "Which Geoffrey Litt concept maps to the Decisions database in Notion?",
        "options": [
            "Explanations",
            "Micro worlds",
            "Shared spaces",
            "Literate programming",
        ],
        "answer": 2,
    },
    {
        "id": "Q4",
        "question": "When can a run be marked Approved in the HITL gate?",
        "options": [
            "When the agent finishes scanning",
            "Only when quiz passed or explicitly waived",
            "When all files are auto_ok",
            "Never — always manual",
        ],
        "answer": 1,
    },
    {
        "id": "Q5",
        "question": "What does the microworld scrubber let a reviewer do?",
        "options": [
            "Edit production scanner code",
            "Step through synthetic agent reasoning per finding",
            "Connect to live Notion",
            "Upload to Google Drive",
        ],
        "answer": 1,
    },
]


def write_findings(scan: ScanOutput, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "findings.json"
    path.write_text(json.dumps(scan.to_dict(), indent=2), encoding="utf-8")
    return path


def write_explainer(scan: ScanOutput, out_dir: Path) -> Path:
    notion_dir = out_dir / "notion"
    notion_dir.mkdir(parents=True, exist_ok=True)
    path = notion_dir / "explainer.md"

    lines = [
        f"# HITL Explainer — {scan.company}",
        "",
        f"**Run ID:** `{scan.run_id}`  ",
        f"**Scanned at:** {scan.scanned_at}  ",
        f"**Fixture root:** `{scan.fixture_root}`",
        "",
        "> **Gate note:** Approved only if quiz passed or waived.",
        "",
        "---",
        "",
        "## Background",
        "",
        "This run scanned the **VertiGreen Robotics** synthetic dataroom fixture — "
        "a fictional cleantech startup used to test human-in-the-loop review loops. "
        "No real client documents, credentials, or Teclogi data are involved.",
        "",
        "The scanner applies deterministic rules (credential patterns, partial IBANs, "
        "legal ambiguity, unaudited financials) and labels each file:",
        "",
        "- `auto_ok` — safe to include with standard diligence",
        "- `needs_human` — reviewer must confirm before external share",
        "- `unclear` — conflicting signals; legal or financial follow-up",
        "",
        "## Intuition",
        "",
        "Think of each finding as a **ticket** in a shared review queue. The agent proposes "
        "a label and action; the human owns the final decision and rationale. "
        "Explanations (this doc) build shared mental models; the microworld lets you "
        "replay *how* the agent reasoned; the Notion Decisions DB is the multiplayer surface.",
        "",
        "## Literate walkthrough",
        "",
        f"**Summary:** {scan.to_dict()['summary']['total']} files scanned — "
        f"{scan.to_dict()['summary']['auto_ok']} auto_ok, "
        f"{scan.to_dict()['summary']['needs_human']} needs_human, "
        f"{scan.to_dict()['summary']['unclear']} unclear.",
        "",
    ]

    for f in scan.findings:
        lines.extend([
            f"### {f.finding_id}: `{f.fixture_path}`",
            "",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| Pillar | {f.pillar} |",
            f"| Agent label | `{f.label}` |",
            f"| Expected (fixture) | `{f.expected_label}` |",
            f"| Rule fired | `{f.rule_fired}` |",
            f"| Suggested action | `{f.agent_suggestion}` |",
            "",
            "**Reasoning steps:**",
            "",
        ])
        for step in f.reasoning_steps:
            match_note = f" — matched: `{step.matched_text}`" if step.matched_text else ""
            lines.append(f"{step.step}. **{step.rule_id}:** {step.description}{match_note}")
        lines.extend(["", f"> Excerpt: _{f.excerpt[:200]}…_", "", "---", ""])

    lines.extend([
        "## Quiz",
        "",
        "Answer all five before marking the run Approved (or record a waiver in Notion).",
        "",
    ])
    for q in QUIZ_QUESTIONS:
        lines.append(f"**{q['id']}.** {q['question']}")
        for j, opt in enumerate(q["options"]):
            lines.append(f"   - ({chr(65 + j)}) {opt}")
        lines.append("")

    lines.extend([
        "### Answer key (for reviewer self-check)",
        "",
    ])
    for q in QUIZ_QUESTIONS:
        letter = chr(65 + q["answer"])
        lines.append(f"- {q['id']}: **{letter}** — {q['options'][q['answer']]}")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_decisions_csv(scan: ScanOutput, out_dir: Path) -> Path:
    notion_dir = out_dir / "notion"
    notion_dir.mkdir(parents=True, exist_ok=True)
    path = notion_dir / "decisions.csv"

    fieldnames = [
        "Finding ID",
        "Fixture path",
        "Agent suggestion",
        "Human decision",
        "Rationale",
        "Quiz passed",
        "Status",
        "Run link",
        "Reviewer",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for f in scan.findings:
            writer.writerow({
                "Finding ID": f.finding_id,
                "Fixture path": f.fixture_path,
                "Agent suggestion": f"{f.label} → {f.agent_suggestion}",
                "Human decision": "",
                "Rationale": "",
                "Quiz passed": "",
                "Status": "pending",
                "Run link": f"out/findings.json#{f.finding_id}",
                "Reviewer": "",
            })
    return path


def write_decisions_json(scan: ScanOutput, out_dir: Path) -> Path:
    notion_dir = out_dir / "notion"
    notion_dir.mkdir(parents=True, exist_ok=True)
    path = notion_dir / "decisions.json"

    rows = [
        {
            "finding_id": f.finding_id,
            "fixture_path": f.fixture_path,
            "agent_suggestion": f.agent_suggestion,
            "agent_label": f.label,
            "human_decision": None,
            "rationale": None,
            "quiz_passed": None,
            "status": "pending",
            "run_link": f"out/findings.json#{f.finding_id}",
            "reviewer": None,
        }
        for f in scan.findings
    ]
    path.write_text(
        json.dumps({"run_id": scan.run_id, "decisions": rows}, indent=2),
        encoding="utf-8",
    )
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="HITL demo — synthetic fixture scan")
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        default=FIXTURE_DIR,
        help="Path to sample dataroom fixtures",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT,
        help="Output directory (default: ./out)",
    )
    parser.add_argument("--run-id", default=None, help="Optional run ID override")
    args = parser.parse_args()

    if not args.fixture_dir.exists():
        print(f"ERROR: fixture dir not found: {args.fixture_dir}", file=sys.stderr)
        return 1

    print(f"Scanning fixtures in {args.fixture_dir} ...")
    scan = scan_fixtures(args.fixture_dir, run_id=args.run_id)

    findings_path = write_findings(scan, args.out_dir)
    explainer_path = write_explainer(scan, args.out_dir)
    csv_path = write_decisions_csv(scan, args.out_dir)
    json_path = write_decisions_json(scan, args.out_dir)

    summary = scan.to_dict()["summary"]
    print(f"\n✓ Findings:  {findings_path}")
    print(f"✓ Explainer: {explainer_path}")
    print(f"✓ Decisions: {csv_path}")
    print(f"           {json_path}")
    print(
        f"\n{summary['total']} findings — "
        f"{summary['auto_ok']} auto_ok, "
        f"{summary['needs_human']} needs_human, "
        f"{summary['unclear']} unclear"
    )
    print(f"\nPlayground: open understanding-lab/playground/ (see understanding-lab/playground/README.md)")
    print(f"Notion spec: hitl/NOTION-HITL.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
