"""
scanner/upload.py
Upload HTML + PDF to the shared CTH Google Drive reports folder.

Uses Google Drive API (service account).
Folder structure:
  Reports / {YYYY-MM} / {company-slug} / {slug}-{YYYY-MM}.html + .pdf
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from scanner.config import (
    DRIVE_REPORTS_FOLDER_ID,
    assert_not_becaps_folder,
)
from scanner.drive_client import DriveClient

logger = logging.getLogger(__name__)

MIME_TYPES = {
    ".html": "text/html",
    ".pdf": "application/pdf",
}


def get_drive_folder_url(folder_id: str) -> str:
    return f"https://drive.google.com/drive/folders/{folder_id}"


def get_drive_file_url(file_id: str) -> str:
    return f"https://drive.google.com/file/d/{file_id}/view"


def upload_report(
    html_path: str,
    pdf_path: str | None,
    slug: str,
    scan_date: str,
    *,
    reports_folder_id: str | None = None,
    drive: DriveClient | None = None,
) -> dict[str, str]:
    """
    Upload HTML (+ optional PDF) to Drive under Reports/{YYYY-MM}/{slug}/.
    Returns dict with folder_id, html_file_id, pdf_file_id (if uploaded).
    """
    parent_id = reports_folder_id or DRIVE_REPORTS_FOLDER_ID
    assert_not_becaps_folder(parent_id, "upload reports")

    client = drive or DriveClient()
    month = scan_date[:7]  # YYYY-MM

    month_folder_id = client.find_or_create_folder(month, parent_id)
    company_folder_id = client.find_or_create_folder(slug, month_folder_id)

    html_name = f"{slug}-{month}.html"
    html_file_id = client.upload_file(html_path, company_folder_id, html_name)

    result = {
        "folder_id": company_folder_id,
        "folder_url": get_drive_folder_url(company_folder_id),
        "html_file_id": html_file_id,
        "html_url": get_drive_file_url(html_file_id),
    }

    if pdf_path and Path(pdf_path).exists():
        pdf_name = f"{slug}-{month}.pdf"
        pdf_file_id = client.upload_file(pdf_path, company_folder_id, pdf_name)
        result["pdf_file_id"] = pdf_file_id
        result["pdf_url"] = get_drive_file_url(pdf_file_id)
    else:
        logger.warning("upload: PDF not found at %s — HTML only uploaded", pdf_path)

    logger.info("upload: reports → %s", result["folder_url"])
    return result
