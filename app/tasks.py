"""
app/tasks.py
RQ worker task — runs the scan pipeline asynchronously.
"""

from __future__ import annotations

import logging

from scanner.runner import ScanRequest, run_scan

logger = logging.getLogger(__name__)


def run_scan_job(
    drive_url: str,
    company_name: str,
    lang: str = "es",
    context_notes: str = "",
) -> dict:
    """Enqueue target for RQ worker."""
    req = ScanRequest(
        drive_url_or_id=drive_url,
        company_name=company_name,
        lang=lang,
        context_notes=context_notes,
    )
    result = run_scan(req)
    logger.info(result.summary())
    return {
        "summary": result.summary(),
        "company_name": result.company_name,
        "slug": result.slug,
        "overall_score": result.overall_score,
        "recommendation": result.recommendation,
        "html_path": result.html_path,
        "pdf_path": result.pdf_path,
        "drive_folder_url": result.drive_folder_url,
        "errors": result.errors,
    }
