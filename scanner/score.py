"""
scanner/score.py
Defines the 8-pillar scoring output schema.

Claude produces this JSON structure after analyzing the Drive tree.
The render.py script injects it into the HTML template.
"""

SCORING_OUTPUT_SCHEMA = {
    "company": {
        "name": "string",
        "sector": "string",
        "country": "string",
        "stage": "pre_seed | seed | series_a",
        "round_target_usd": "number | null",
        "language": "es | en",
        "scan_date": "YYYY-MM-DD",
        "drive_folder_id": "string",
    },
    "overall": {
        "score": "float 1.0-5.0",                 # average of 8 pillars
        "recommendation": "go_phase1 | tier2 | not_ready | decline",
        "verdict_title": "string — max 8 words",
        "verdict_body": "string — 3-4 sentences",
    },
    "eligibility": {
        "stage":        {"value": "string", "result": "pass | warn | fail", "note": "string"},
        "round_size":   {"value": "number", "result": "pass | warn | fail", "note": "string"},
        "climate_fit":  {"value": "string", "result": "pass | warn | fail", "note": "string"},
        "exclusivity":  {"value": "tbd",    "result": "pass | warn | fail", "note": "string"},
        "co_creation":  {"value": "string", "result": "pass | warn | fail", "note": "string"},
    },
    "pillars": {
        "bm": {
            "score": "float",
            "status": "strong | emerging | developing | partial | needs_work",
            "summary": "string — 1-2 sentences",
            "strengths": ["string"],
            "gaps": ["string"],
            "missing_docs": ["string"],
            "cth_actions_p1": ["string"],
            "docs_present": ["string"],
            "docs_weak": ["string"],
            "docs_missing": ["string"],
        },
        # team, traction, financials, impact, legal, market, investor_readiness
        # all follow the same schema as bm above
    },
    "key_metrics": [
        {"label": "string", "value": "string", "sub": "string"},
        # 5 items: round target, raised to date, Y1 revenue, pilots/contracts, other
    ],
    "action_plan_p1": ["string"],   # 6-8 concrete actions for Phase 1
    "action_plan_p2": ["string"],   # 4-5 items for Phase 2 track
}

# Scoring thresholds (from cth-growth-services.md)
THRESHOLDS = {
    "tier1_candidate": 4.0,
    "tier2_pipeline": 3.0,
    "not_ready": 0.0,
    "round_minimum_usd": 1_000_000,
}


def score_to_status(score: float) -> str:
    """Convert a numeric score (1.0–5.0) to a status label."""
    if score >= 4.0:
        return "strong"
    if score >= 3.5:
        return "emerging"
    if score >= 3.0:
        return "developing"
    if score >= 2.5:
        return "partial"
    return "needs_work"


STATUS_LABELS = {
    "es": {
        "strong": "Sólido",
        "emerging": "Emergente",
        "developing": "En desarrollo",
        "partial": "Parcial",
        "needs_work": "Requiere trabajo",
    },
    "en": {
        "strong": "Strong",
        "emerging": "Emerging",
        "developing": "Developing",
        "partial": "Partial",
        "needs_work": "Needs Work",
    },
}


PILLAR_ORDER = [
    "bm", "team", "traction", "financials",
    "impact", "legal", "market", "investor_readiness",
]

PILLAR_NAMES = {
    "es": {
        "bm": "Modelo de Negocio",
        "team": "Equipo",
        "traction": "Tracción",
        "financials": "Finanzas",
        "impact": "Impacto",
        "legal": "Legal & IP",
        "market": "Mercado",
        "investor_readiness": "Preparación para Inversión",
    },
    "en": {
        "bm": "Business Model",
        "team": "Team",
        "traction": "Traction",
        "financials": "Financials",
        "impact": "Impact",
        "legal": "Legal & IP",
        "market": "Market",
        "investor_readiness": "Investor Readiness",
    },
}
