"""
scanner/findings_from_score.py
Convert scoring JSON (and optional crawl tree) into reviewable HITL findings.

Also normalizes fixture microworld findings so one reviewer UI can load both shapes.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scanner.score import PILLAR_ORDER, PILLAR_NAMES

# Pillar status → agent label for gap/doc findings
_STATUS_TO_LABEL = {
    "needs_work": "needs_human",
    "partial": "needs_human",
    "developing": "unclear",
    "emerging": "unclear",
    "strong": "auto_ok",
}

_ELIGIBILITY_RESULT_TO_LABEL = {
    "fail": "needs_human",
    "warn": "unclear",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _label_for_pillar_item(status: str) -> str:
    return _STATUS_TO_LABEL.get(status, "unclear")


def _suggestion_for_rule(rule: str, text: str) -> str:
    suggestions = {
        "score_gap": "address_gap",
        "missing_doc": "request_document",
        "weak_doc": "strengthen_document",
        "eligibility_fail": "resolve_eligibility",
        "eligibility_warn": "confirm_eligibility",
        "pillar_strong": "include_in_report",
    }
    base = suggestions.get(rule, "review_item")
    snippet = text[:60].strip()
    return f"{base}: {snippet}" if snippet else base


def findings_from_score(
    scoring: dict[str, Any],
    *,
    source: str = "live_scan",
    run_id: str | None = None,
    tree: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Map SCORING_OUTPUT_SCHEMA JSON to reviewable findings (S-prefixed IDs).

    Mapping (see README Production reviewer section):
    - pillars.gaps / missing_docs / docs_weak → findings (label from pillar status)
    - eligibility fail/warn → findings
    - strong pillars with only strengths → one auto_ok summary finding (optional, sparse)
    """
    company = scoring.get("company", {})
    company_name = company.get("name", "Unknown")
    scan_date = company.get("scan_date", datetime.now(timezone.utc).date().isoformat())
    lang = company.get("language", "es")
    rid = run_id or f"scan-{scan_date.replace('-', '')}"

    findings: list[dict[str, Any]] = []
    seq = 0

    def add_finding(
        *,
        pillar: str,
        source_path: str,
        label: str,
        rule_fired: str,
        excerpt: str,
        reasoning: list[dict[str, Any]] | None = None,
    ) -> None:
        nonlocal seq
        seq += 1
        finding_id = f"S{seq:03d}"
        findings.append(
            {
                "finding_id": finding_id,
                "source_path": source_path,
                "pillar": pillar,
                "label": label,
                "agent_suggestion": _suggestion_for_rule(rule_fired, excerpt),
                "rule_fired": rule_fired,
                "excerpt": excerpt[:500],
                "reasoning_steps": reasoning
                or [{"step": 1, "description": f"Rule {rule_fired} fired for {source_path}"}],
            }
        )

    pillars = scoring.get("pillars", {})
    for pillar_key in PILLAR_ORDER:
        pillar = pillars.get(pillar_key, {})
        if not pillar:
            continue
        status = pillar.get("status", "developing")
        pillar_label = PILLAR_NAMES.get(lang, PILLAR_NAMES["en"]).get(pillar_key, pillar_key)
        label = _label_for_pillar_item(status)

        for gap in pillar.get("gaps", []):
            add_finding(
                pillar=pillar_key,
                source_path=f"pillar:{pillar_key}|gap:{gap[:80]}",
                label=label,
                rule_fired="score_gap",
                excerpt=f"[{pillar_label}] Gap: {gap}",
                reasoning=[
                    {"step": 1, "description": f"Pillar status is {status}"},
                    {"step": 2, "description": f"Gap identified: {gap}"},
                ],
            )

        for doc in pillar.get("missing_docs", []):
            add_finding(
                pillar=pillar_key,
                source_path=f"pillar:{pillar_key}|missing:{doc[:80]}",
                label=label,
                rule_fired="missing_doc",
                excerpt=f"[{pillar_label}] Missing document: {doc}",
                reasoning=[
                    {"step": 1, "description": f"Pillar status is {status}"},
                    {"step": 2, "description": f"Expected doc not found: {doc}"},
                ],
            )

        for doc in pillar.get("docs_weak", []):
            add_finding(
                pillar=pillar_key,
                source_path=f"pillar:{pillar_key}|weak:{doc[:80]}",
                label=label,
                rule_fired="weak_doc",
                excerpt=f"[{pillar_label}] Weak document: {doc}",
                reasoning=[
                    {"step": 1, "description": f"Pillar status is {status}"},
                    {"step": 2, "description": f"Document present but weak: {doc}"},
                ],
            )

        gaps = pillar.get("gaps", [])
        missing = pillar.get("missing_docs", [])
        weak = pillar.get("docs_weak", [])
        strengths = pillar.get("strengths", [])
        if (
            status == "strong"
            and not gaps
            and not missing
            and not weak
            and strengths
        ):
            summary = "; ".join(strengths[:3])
            add_finding(
                pillar=pillar_key,
                source_path=f"pillar:{pillar_key}|summary",
                label="auto_ok",
                rule_fired="pillar_strong",
                excerpt=f"[{pillar_label}] Strengths: {summary}",
                reasoning=[
                    {"step": 1, "description": f"Pillar scored strong with no gaps"},
                    {"step": 2, "description": summary},
                ],
            )

    eligibility = scoring.get("eligibility", {})
    for key, entry in eligibility.items():
        if not isinstance(entry, dict):
            continue
        result = entry.get("result", "pass")
        if result == "pass":
            continue
        el_label = _ELIGIBILITY_RESULT_TO_LABEL.get(result, "unclear")
        note = entry.get("note", "")
        value = entry.get("value", "")
        add_finding(
            pillar="eligibility",
            source_path=f"eligibility:{key}",
            label=el_label,
            rule_fired=f"eligibility_{result}",
            excerpt=f"Eligibility {key}: {value} — {note}",
            reasoning=[
                {"step": 1, "description": f"Eligibility check {key} returned {result}"},
                {"step": 2, "description": note or str(value)},
            ],
        )

    return {
        "run_id": rid,
        "company": company_name,
        "source": source,
        "scanned_at": _now_iso(),
        "scan_date": scan_date,
        "findings": findings,
        "summary": _summarize(findings),
        "crawl_meta": _crawl_meta(tree) if tree else None,
    }


def _summarize(findings: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(findings),
        "auto_ok": sum(1 for f in findings if f["label"] == "auto_ok"),
        "needs_human": sum(1 for f in findings if f["label"] == "needs_human"),
        "unclear": sum(1 for f in findings if f["label"] == "unclear"),
    }


def _crawl_meta(tree: dict[str, Any]) -> dict[str, Any]:
    return {
        "folder_id": tree.get("folder_id"),
        "total_files": tree.get("total_files"),
        "total_folders": tree.get("total_folders"),
    }


def normalize_findings_doc(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Unify fixture microworld and production score findings for the reviewer UI.

    Accepts:
    - Production: { findings: [...], source_path on each item }
    - Fixture: { findings | gate_findings, fixture_path on each item }
    """
    findings_raw = raw.get("findings") or raw.get("gate_findings") or []
    normalized: list[dict[str, Any]] = []

    for item in findings_raw:
        f = dict(item)
        if "source_path" not in f and "fixture_path" in f:
            f["source_path"] = f["fixture_path"]
        if "fixture_path" not in f and "source_path" in f:
            f["fixture_path"] = f["source_path"]
        steps = f.get("reasoning_steps") or []
        f["reasoning_steps"] = [
            {
                "step": s.get("step", i + 1),
                "description": s.get("description") or s.get("rule_id", ""),
                **({"matched_text": s["matched_text"]} if s.get("matched_text") else {}),
            }
            for i, s in enumerate(steps)
        ]
        normalized.append(f)

    return {
        "run_id": raw.get("run_id", "unknown"),
        "company": raw.get("company", "Unknown"),
        "source": raw.get("source", "fixture" if raw.get("fixture_root") else "unknown"),
        "scanned_at": raw.get("scanned_at", _now_iso()),
        "findings": normalized,
        "summary": raw.get("summary") or _summarize(normalized),
        "fixture_root": raw.get("fixture_root"),
    }


def findings_output_path(slug: str, scan_date: str, output_dir: str | Path) -> Path:
    """Sibling to HTML report: output/{slug}-{YYYY-MM}.findings.json"""
    month = scan_date[:7]
    return Path(output_dir) / f"{slug}-{month}.findings.json"


def findings_path_for_html(html_path: str | Path) -> Path:
    """Derive findings path from an existing HTML report path."""
    p = Path(html_path)
    return p.with_name(p.stem + ".findings.json")


def save_findings(doc: dict[str, Any], path: str | Path) -> str:
    """Persist findings JSON; return path string."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(p)


def load_findings(path: str | Path) -> dict[str, Any]:
    return normalize_findings_doc(json.loads(Path(path).read_text(encoding="utf-8")))


def fixture_scan_to_findings(scan_output: dict[str, Any]) -> dict[str, Any]:
    """Convert fixture_scan ScanOutput dict to normalized production-compatible doc."""
    doc = dict(scan_output)
    doc["source"] = "fixture"
    return normalize_findings_doc(doc)
