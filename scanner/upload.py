"""
scanner/upload.py
Upload HTML + PDF to the shared CTH Google Drive reports folder.

Uses the Google Drive MCP (already authenticated via Claude Desktop).

NOTE: In a Claude Code in-session context, Claude calls the Drive MCP tools
directly. This file documents the data contract and the folder structure.

The actual upload is performed by Claude via:
  - Google Drive:create_file  (for HTML and PDF)

Folder structure in Drive:
  CTH Growth Services (shared team folder)
  └── Reports/
      └── {YYYY-MM}/
          └── {company-slug}/
              ├── {slug}-{YYYY-MM}.html
              └── {slug}-{YYYY-MM}.pdf

The parent folder ID is stored in .env as DRIVE_REPORTS_FOLDER_ID.
Set this once — it's the ID of the "Reports/" folder inside CTH Growth Services.
"""

import os

# Folder structure constants
DRIVE_REPORTS_FOLDER_ID = os.getenv(
    "DRIVE_REPORTS_FOLDER_ID", "1RvuoSvbm6SvbdCWU06Wa7jyfEniPmzbP"
)

# MIME types for Drive upload
MIME_TYPES = {
    ".html": "text/html",
    ".pdf": "application/pdf",
}

# ── In-session Claude Code upload flow ────────────────────────────────────────
#
# Claude performs these steps via the Google Drive MCP tools:
#
# 1. Check if month subfolder exists:
#    Google Drive:search_files query: "name='{YYYY-MM}' and '{REPORTS_FOLDER_ID}' in parents"
#
# 2. If not: create it
#    Google Drive:create_file name='{YYYY-MM}' mimeType='application/vnd.google-apps.folder'
#
# 3. Check if company subfolder exists inside month folder:
#    Google Drive:search_files query: "name='{slug}' and '{month_folder_id}' in parents"
#
# 4. If not: create it
#    Google Drive:create_file name='{slug}' mimeType='application/vnd.google-apps.folder'
#
# 5. Upload HTML:
#    Google Drive:create_file
#      title='{slug}-{YYYY-MM}.html'
#      content=<base64 HTML>
#      mimeType='text/html'
#      parentId='{company_folder_id}'
#      disableConversionToGoogleType=true
#
# 6. Upload PDF:
#    Google Drive:create_file
#      title='{slug}-{YYYY-MM}.pdf'
#      content=<base64 PDF>
#      mimeType='application/pdf'
#      parentId='{company_folder_id}'
#      disableConversionToGoogleType=true
#
# 7. Print Drive folder URL:
#    https://drive.google.com/drive/folders/{company_folder_id}


def get_drive_folder_url(folder_id: str) -> str:
    return f"https://drive.google.com/drive/folders/{folder_id}"


def get_drive_file_url(file_id: str) -> str:
    return f"https://drive.google.com/file/d/{file_id}/view"
