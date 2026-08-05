"""
scanner/render.py
Takes the scoring JSON and injects values into the report HTML template.
Uses Python string formatting (no external template engine needed).
"""

import re
from datetime import date, datetime
from pathlib import Path


def render_report(scoring: dict, lang: str = "es") -> str:
    """
    Inject scoring JSON into templates/report.html.
    Returns the final HTML string.
    """
    template_path = Path(__file__).parent.parent / "templates" / "report.html"
    template = template_path.read_text(encoding="utf-8")

    company = scoring["company"]
    overall = scoring["overall"]
    pillars = scoring["pillars"]
    eligibility = scoring["eligibility"]

    scan_date = company.get("scan_date", date.today().isoformat())

    # ── Top-level substitutions ───────────────────────────────────────────────
    replacements = {
        "{{company_name}}":       company["name"],
        "{{company_tagline}}":    f"{company.get('sector', '')} · {company.get('country', '')}",
        "{{scan_date}}":          _format_date(scan_date, lang),
        "{{round_target}}":       _format_usd(company.get("round_target_usd")),
        "{{stage}}":              company.get("stage", ""),
        "{{overall_score}}":      str(overall["score"]),
        "{{cth_recommendation}}": _format_rec(overall["recommendation"], lang),
        "{{verdict_title}}":      overall["verdict_title"],
        "{{verdict_body}}":       overall["verdict_body"],
        "{{overall_score_pct}}":  str(int(overall["score"] / 5.0 * 100)),
    }

    # ── Key metrics (5 cards) ─────────────────────────────────────────────────
    for i, metric in enumerate(scoring.get("key_metrics", [])[:5], 1):
        replacements[f"{{{{metric_{i}_label}}}}"] = metric.get("label", "")
        replacements[f"{{{{metric_{i}_value}}}}"] = metric.get("value", "—")
        replacements[f"{{{{metric_{i}_sub}}}}"] = metric.get("sub", "")

    # ── Pillar cards (scorecard grid) ─────────────────────────────────────────
    PILLAR_ORDER = [
        "bm", "team", "traction", "financials",
        "impact", "legal", "market", "investor_readiness",
    ]
    for pillar_id in PILLAR_ORDER:
        p = pillars.get(pillar_id, {})
        score = p.get("score", 0)
        status = p.get("status", "needs_work")
        replacements[f"{{{{{pillar_id}_score}}}}"] = str(score)
        replacements[f"{{{{{pillar_id}_status}}}}"] = _status_label(status, lang)
        replacements[f"{{{{{pillar_id}_summary}}}}"] = p.get("summary", "")
        replacements[f"{{{{{pillar_id}_color}}}}"] = _score_color(score)

    # ── Pillar deep dive sections ─────────────────────────────────────────────
    for pillar_id in PILLAR_ORDER:
        p = pillars.get(pillar_id, {})
        replacements[f"{{{{{pillar_id}_strengths}}}}"] = _render_list(p.get("strengths", []))
        replacements[f"{{{{{pillar_id}_gaps}}}}"] = _render_list(p.get("gaps", []))
        replacements[f"{{{{{pillar_id}_missing}}}}"] = _render_list(p.get("missing_docs", []))
        replacements[f"{{{{{pillar_id}_actions}}}}"] = _render_list(p.get("cth_actions_p1", []))
        replacements[f"{{{{{pillar_id}_docs_present}}}}"] = _render_doc_tags(p.get("docs_present", []), "p")
        replacements[f"{{{{{pillar_id}_docs_weak}}}}"] = _render_doc_tags(p.get("docs_weak", []), "w")
        replacements[f"{{{{{pillar_id}_docs_missing}}}}"] = _render_doc_tags(p.get("docs_missing", []), "m")

    # ── Eligibility table ─────────────────────────────────────────────────────
    for criterion, data in eligibility.items():
        result = data.get("result", "warn")
        replacements[f"{{{{elig_{criterion}_value}}}}"] = str(data.get("value", ""))
        replacements[f"{{{{elig_{criterion}_result}}}}"] = _elig_label(result, lang)
        replacements[f"{{{{elig_{criterion}_note}}}}"] = data.get("note", "")
        replacements[f"{{{{elig_{criterion}_class}}}}"] = result  # css class

    # ── Action plan ───────────────────────────────────────────────────────────
    replacements["{{action_plan_p1}}"] = _render_action_list(scoring.get("action_plan_p1", []))
    replacements["{{action_plan_p2}}"] = _render_action_list(scoring.get("action_plan_p2", []))

    # ── Apply all replacements ────────────────────────────────────────────────
    html = template
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, str(value))

    return html


# ── Helpers ───────────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _format_date(iso_date: str, lang: str) -> str:
    d = datetime.fromisoformat(iso_date)
    if lang == "es":
        months = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
        ]
        return f"{d.day} de {months[d.month - 1]}, {d.year}"
    return d.strftime("%B %d, %Y")


def _format_usd(amount) -> str:
    if not amount:
        return "N/D"
    return f"USD {int(amount):,}".replace(",", ".")


def _score_color(score: float) -> str:
    if score >= 4.0:
        return "verde"
    if score >= 3.0:
        return "ambar"
    return "rojo"


def _status_label(status: str, lang: str) -> str:
    labels = {
        "es": {
            "strong": "✓ Sólido", "emerging": "⚡ Emergente",
            "developing": "⚡ En desarrollo", "partial": "⚡ Parcial",
            "needs_work": "✗ Requiere trabajo",
        },
        "en": {
            "strong": "✓ Strong", "emerging": "⚡ Emerging",
            "developing": "⚡ Developing", "partial": "⚡ Partial",
            "needs_work": "✗ Needs Work",
        },
    }
    return labels.get(lang, labels["es"]).get(status, status)


def _elig_label(result: str, lang: str) -> str:
    labels = {
        "es": {"pass": "✓ Aprueba", "warn": "⚡ Parcial", "fail": "✗ No cumple"},
        "en": {"pass": "✓ Pass", "warn": "⚡ Partial", "fail": "✗ Fail"},
    }
    return labels.get(lang, labels["es"]).get(result, result)


def _format_rec(rec: str, lang: str) -> str:
    labels = {
        "es": {
            "go_phase1": "SÍ — Fase 1", "tier2": "Tier 2 — Pipeline",
            "not_ready": "No listo aún", "decline": "Declinar",
        },
        "en": {
            "go_phase1": "GO — Phase 1", "tier2": "Tier 2 — Pipeline",
            "not_ready": "Not Ready", "decline": "Decline",
        },
    }
    return labels.get(lang, labels["es"]).get(rec, rec)


def _render_list(items: list) -> str:
    if not items:
        return "<li>—</li>"
    return "".join(f"<li>{item}</li>" for item in items)


def _render_doc_tags(items: list, cls: str) -> str:
    if not items:
        return ""
    icons = {"p": "✓", "w": "⚡", "m": "✗"}
    return "".join(f'<span class="dt {cls}">{icons[cls]} {item}</span>' for item in items)


def _render_action_list(items: list) -> str:
    if not items:
        return "<li>—</li>"
    return "".join(f"<li>{item}</li>" for item in items)


def save_html(html: str, slug: str, scan_date: str, output_dir: str = "output") -> str:
    """Save rendered HTML and return the file path."""
    Path(output_dir).mkdir(exist_ok=True)
    month = scan_date[:7]  # YYYY-MM
    filename = f"{slug}-{month}.html"
    path = f"{output_dir}/{filename}"
    Path(path).write_text(html, encoding="utf-8")
    print(f"HTML saved → {path}")
    return path
