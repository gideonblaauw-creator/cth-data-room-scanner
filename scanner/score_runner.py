"""
scanner/score_runner.py
Headless LLM scorer — produces SCORING_OUTPUT_SCHEMA JSON from a Drive tree.

Uses Anthropic API with cth-growth-services.md as framework context.
BeCaps 3.5 calibration is the sole benchmark reference.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from scanner.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, REPO_ROOT, SKILLS_DIR
from scanner.score import (
    PILLAR_ORDER,
    SCORING_OUTPUT_SCHEMA,
    THRESHOLDS,
    score_to_status,
)

logger = logging.getLogger(__name__)

BECAPS_REFERENCE = """
BeCaps calibration (READ-ONLY reference — score 3.5/5, GO Phase 1):
- Sector: Agrifood Biotech — Microencapsulation
- Country: Argentina (Buenos Aires), Stage: Seed, Round: USD 2,000,000
- Pillar scores: bm=3.5, team=4.0, traction=3.5, financials=3.0,
  impact=4.0, legal=3.0, market=3.5, investor_readiness=3.5
- Pattern: GO despite no pillar above 4.0 — strong team+impact (2 at 4.0),
  no pillar below 3.0.
"""


def _load_framework() -> str:
    path = SKILLS_DIR / "cth-growth-services.md"
    if not path.exists():
        path = REPO_ROOT / "skills" / "cth-growth-services.md"
    return path.read_text(encoding="utf-8")


def _build_prompt(
    tree: dict[str, Any],
    company_name: str,
    lang: str,
    scan_date: str,
    drive_folder_id: str,
    context_notes: str = "",
) -> str:
    return f"""You are a CTH Growth Services due diligence analyst.
Score the startup data room using the 8-pillar framework below.

{BECAPS_REFERENCE}

## Framework
{_load_framework()}

## Required output
Return ONLY valid JSON matching this schema (no markdown fences):
{json.dumps(SCORING_OUTPUT_SCHEMA, indent=2)}

All 8 pillars must be present: {", ".join(PILLAR_ORDER)}.
Each pillar needs: score, status, summary, strengths, gaps, missing_docs,
cth_actions_p1, docs_present, docs_weak, docs_missing.

## Scan parameters
- company_name: {company_name}
- language: {lang}
- scan_date: {scan_date}
- drive_folder_id: {drive_folder_id}
- Additional context from operator: {context_notes or "none"}

## Data room crawl (JSON)
{json.dumps(tree, ensure_ascii=False, indent=2)[:120000]}
"""


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _normalize_scoring(data: dict[str, Any], company_name: str, lang: str,
                       scan_date: str, drive_folder_id: str) -> dict[str, Any]:
    """Ensure required fields and recompute derived values."""
    company = data.setdefault("company", {})
    company.setdefault("name", company_name)
    company.setdefault("language", lang)
    company.setdefault("scan_date", scan_date)
    company.setdefault("drive_folder_id", drive_folder_id)

    pillars = data.setdefault("pillars", {})
    scores = []
    for pid in PILLAR_ORDER:
        p = pillars.setdefault(pid, {})
        score = float(p.get("score", 3.0))
        p["score"] = round(score, 1)
        p.setdefault("status", score_to_status(score))
        for field in ("summary", "strengths", "gaps", "missing_docs",
                      "cth_actions_p1", "docs_present", "docs_weak", "docs_missing"):
            p.setdefault(field, [] if field != "summary" else "")
        scores.append(p["score"])

    overall = data.setdefault("overall", {})
    if scores:
        avg = round(sum(scores) / len(scores), 1)
        overall["score"] = avg
    overall.setdefault("recommendation", _recommendation(overall.get("score", 3.0), pillars))
    overall.setdefault("verdict_title", "Evaluación pendiente de revisión")
    overall.setdefault("verdict_body", "")

    data.setdefault("eligibility", {})
    data.setdefault("key_metrics", [])
    data.setdefault("action_plan_p1", [])
    data.setdefault("action_plan_p2", [])
    return data


def _recommendation(overall: float, pillars: dict) -> str:
    high = sum(1 for p in pillars.values() if float(p.get("score", 0)) >= 4.0)
    if overall >= THRESHOLDS["tier1_candidate"]:
        return "go_phase1"
    if overall >= 3.5 and high >= 2:
        return "go_phase1"
    if overall >= THRESHOLDS["tier2_pipeline"]:
        return "tier2"
    if overall >= 2.0:
        return "not_ready"
    return "decline"


def score_data_room(
    tree: dict[str, Any],
    company_name: str,
    *,
    lang: str = "es",
    scan_date: str | None = None,
    drive_folder_id: str | None = None,
    context_notes: str = "",
    api_key: str | None = None,
) -> dict[str, Any]:
    """
    Call LLM to score a crawled data room tree.
    Returns SCORING_OUTPUT_SCHEMA dict.
    """
    from datetime import date

    scan_date = scan_date or date.today().isoformat()
    drive_folder_id = drive_folder_id or tree.get("folder_id", "")
    key = api_key or ANTHROPIC_API_KEY

    if not key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not set — required for headless scoring."
        )

    import anthropic

    client = anthropic.Anthropic(api_key=key)
    prompt = _build_prompt(
        tree, company_name, lang, scan_date, drive_folder_id, context_notes
    )

    message = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text
    data = _extract_json(raw)
    return _normalize_scoring(data, company_name, lang, scan_date, drive_folder_id)


def load_becaps_fixture() -> dict[str, Any]:
    """BeCaps 3.5 calibration fixture for dry-run / tests (no LLM)."""
    fixture_path = REPO_ROOT / "fixtures" / "becaps_scoring.json"
    if fixture_path.exists():
        return json.loads(fixture_path.read_text(encoding="utf-8"))
    # Inline fallback
    return {
        "company": {
            "name": "BeCaps",
            "sector": "Agrifood Biotech — Microencapsulation",
            "country": "Argentina",
            "stage": "seed",
            "round_target_usd": 2_000_000,
            "language": "es",
            "scan_date": "2026-04-15",
            "drive_folder_id": "1sg4TlFoP2_YVYmDdxuacC3Gs4kpB0Bd_",
        },
        "overall": {
            "score": 3.5,
            "recommendation": "go_phase1",
            "verdict_title": "Fundación sólida con brechas abordables",
            "verdict_body": (
                "BeCaps presenta un equipo fuerte y narrativa de impacto clara. "
                "Las finanzas y la estructura legal requieren trabajo antes de "
                "una ronda institucional, pero el perfil califica para Fase 1 CTH."
            ),
        },
        "eligibility": {
            "stage": {"value": "Seed", "result": "pass", "note": "Etapa adecuada"},
            "round_size": {"value": "2000000", "result": "pass", "note": "≥ USD 1M"},
            "climate_fit": {"value": "Agrifood sostenible", "result": "pass", "note": "Tesis climática directa"},
            "exclusivity": {"value": "tbd", "result": "warn", "note": "Confirmar con founders"},
            "co_creation": {"value": "Abierto", "result": "pass", "note": "Interés en modelo CTH"},
        },
        "pillars": {
            pid: {
                "score": s,
                "status": score_to_status(s),
                "summary": f"Referencia BeCaps — pilar {pid}.",
                "strengths": ["Fortaleza de calibración"],
                "gaps": ["Brecha de calibración"],
                "missing_docs": [],
                "cth_actions_p1": ["Acción Fase 1 de ejemplo"],
                "docs_present": ["Documento de referencia"],
                "docs_weak": [],
                "docs_missing": [],
            }
            for pid, s in {
                "bm": 3.5, "team": 4.0, "traction": 3.5, "financials": 3.0,
                "impact": 4.0, "legal": 3.0, "market": 3.5, "investor_readiness": 3.5,
            }.items()
        },
        "key_metrics": [
            {"label": "Ronda objetivo", "value": "USD 2.0M", "sub": "Seed"},
            {"label": "Recaudado", "value": "N/D", "sub": "Pre-seed"},
            {"label": "Ingresos Y1", "value": "Pre-revenue", "sub": "Pilots activos"},
            {"label": "Pilotos", "value": "3", "sub": "LOIs firmadas"},
            {"label": "Runway", "value": "9 meses", "sub": "Estimado"},
        ],
        "action_plan_p1": [
            "Completar modelo financiero 3 años",
            "Formalizar cap table y acuerdos de founders",
            "Rediseñar pitch deck con narrativa CTH",
            "Estructurar medición de impacto",
            "Organizar data room con índice",
            "Preparar lista de inversores objetivo",
        ],
        "action_plan_p2": [
            "Introducciones activas a red CTH",
            "Preparación de due diligence",
            "Soporte en negociación de term sheet",
        ],
    }
