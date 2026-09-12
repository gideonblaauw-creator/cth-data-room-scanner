"""
scanner/runner.py
Headless orchestrator for scan.md steps 1–7.

  1. Parse input (folder URL/ID, lang, company name)
  2. Crawl Drive folder
  3. Score across 8 pillars (LLM)
  4. Render HTML report
  5. Generate PDF (Playwright)
  6. Upload to shared Drive reports folder
  7. Return summary
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from scanner.config import DRIVE_REPORTS_FOLDER_ID, ensure_output_dir
from scanner.crawl import crawl_folder, extract_folder_id
from scanner.findings_from_score import findings_from_score, save_findings, findings_output_path
from scanner.pdf import convert as pdf_convert
from scanner.render import render_report, save_html, slugify
from scanner.score_runner import load_becaps_fixture, score_data_room
from scanner.upload import upload_report

logger = logging.getLogger(__name__)


@dataclass
class ScanRequest:
    drive_url_or_id: str
    company_name: str
    lang: str = "es"
    context_notes: str = ""
    dry_run: bool = False
    skip_upload: bool = False
    skip_crawl: bool = False


@dataclass
class ScanResult:
    company_name: str
    slug: str
    scan_date: str
    overall_score: float
    recommendation: str
    html_path: str
    pdf_path: str | None
    findings_path: str | None = None
    drive_folder_url: str | None = None
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"✅ Scan complete: {self.company_name}",
            f"   Score: {self.overall_score}/5.0 — {self.recommendation}",
            f"   HTML:  {self.html_path}",
            f"   PDF:   {self.pdf_path or '(not generated)'}",
        ]
        if self.drive_folder_url:
            lines.append(f"   Drive: {self.drive_folder_url}")
        if self.errors:
            lines.append(f"   Warnings: {'; '.join(self.errors)}")
        return "\n".join(lines)


def run_scan(req: ScanRequest) -> ScanResult:
    """Execute the full scan pipeline (steps 1–7)."""
    # Step 1 — Parse input
    folder_id = extract_folder_id(req.drive_url_or_id)
    slug = slugify(req.company_name)
    scan_date = date.today().isoformat()
    output_dir = str(ensure_output_dir())
    errors: list[str] = []

    # Step 2 — Crawl
    if req.dry_run or req.skip_crawl:
        tree = {
            "folder_id": folder_id,
            "folder_name": req.company_name,
            "crawled_at": scan_date,
            "total_files": 0,
            "total_folders": 0,
            "empty_folders": [],
            "items": [],
        }
        logger.info("runner: dry-run — skipping Drive crawl")
    else:
        logger.info("runner: crawling folder %s", folder_id)
        tree = crawl_folder(folder_id)

    # Step 3 — Score
    if req.dry_run:
        logger.info("runner: dry-run — using BeCaps calibration fixture")
        scoring = load_becaps_fixture()
        scoring["company"]["name"] = req.company_name
        scoring["company"]["scan_date"] = scan_date
        scoring["company"]["drive_folder_id"] = folder_id
        scoring["company"]["language"] = req.lang
    else:
        logger.info("runner: scoring data room for %s", req.company_name)
        scoring = score_data_room(
            tree,
            req.company_name,
            lang=req.lang,
            scan_date=scan_date,
            drive_folder_id=folder_id,
            context_notes=req.context_notes,
        )

    # Step 3b — Review findings (before render/upload; audit path independent of upload)
    source = "dry_run" if req.dry_run else "live_scan"
    run_id = f"{slug}-{scan_date}"
    findings_doc = findings_from_score(
        scoring,
        source=source,
        run_id=run_id,
        tree=tree,
    )
    findings_path = None
    try:
        from scanner.findings_from_score import findings_output_path

        fp = findings_output_path(slug, scan_date, output_dir)
        findings_path = save_findings(findings_doc, fp)
        logger.info(
            "runner: wrote %d findings → %s",
            len(findings_doc["findings"]),
            findings_path,
        )
    except Exception as exc:
        errors.append(f"Findings export failed: {exc}")
        logger.exception("runner: findings export failed")

    # Step 4 — Render HTML
    logger.info("runner: rendering HTML report")
    html = render_report(scoring, lang=req.lang)
    html_path = save_html(html, slug, scan_date, output_dir=output_dir)

    # Step 5 — Generate PDF
    pdf_path = html_path.replace(".html", ".pdf")
    pdf_ok = pdf_convert(html_path, pdf_path)
    if not pdf_ok:
        pdf_path = None
        errors.append("PDF generation failed — HTML saved only")

    # Step 6 — Upload to Drive
    drive_url = None
    if not req.skip_upload and not req.dry_run:
        try:
            logger.info("runner: uploading to Drive folder %s", DRIVE_REPORTS_FOLDER_ID)
            upload_result = upload_report(
                html_path, pdf_path, slug, scan_date
            )
            drive_url = upload_result["folder_url"]
        except Exception as exc:
            errors.append(f"Drive upload failed: {exc}")
            logger.exception("runner: upload failed")
    elif req.dry_run:
        logger.info("runner: dry-run — skipping Drive upload")

    overall = scoring.get("overall", {})
    return ScanResult(
        company_name=req.company_name,
        slug=slug,
        scan_date=scan_date,
        overall_score=overall.get("score", 0.0),
        recommendation=overall.get("recommendation", "unknown"),
        html_path=html_path,
        pdf_path=pdf_path,
        findings_path=findings_path,
        drive_folder_url=drive_url,
        errors=errors,
    )
