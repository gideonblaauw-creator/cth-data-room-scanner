"""
scanner/drive_client.py
Google Drive API client (service account). Shared by crawl and upload.
"""

from __future__ import annotations

import io
import logging
import mimetypes
from pathlib import Path
from typing import Any

from scanner.config import GOOGLE_APPLICATION_CREDENTIALS

logger = logging.getLogger(__name__)

# Google Workspace export MIME types
EXPORT_MIME = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}

READABLE_MIME_PREFIXES = (
    "text/",
    "application/pdf",
    "application/json",
    "application/xml",
)


class DriveClient:
    """Thin wrapper around Google Drive API v3."""

    def __init__(self, credentials_path: str | None = None):
        path = credentials_path or GOOGLE_APPLICATION_CREDENTIALS
        if not path or not Path(path).exists():
            raise FileNotFoundError(
                "GOOGLE_APPLICATION_CREDENTIALS not set or file missing. "
                "Provide a service-account JSON via env."
            )
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_file(
            path,
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        self._service = build("drive", "v3", credentials=creds, cache_discovery=False)

    def get_file_metadata(self, file_id: str) -> dict[str, Any]:
        return (
            self._service.files()
            .get(fileId=file_id, fields="id,name,mimeType,size,parents")
            .execute()
        )

    def list_children(self, folder_id: str) -> list[dict[str, Any]]:
        q = f"'{folder_id}' in parents and trashed=false"
        items: list[dict[str, Any]] = []
        page_token = None
        while True:
            resp = (
                self._service.files()
                .list(
                    q=q,
                    fields="nextPageToken,files(id,name,mimeType,size)",
                    pageSize=200,
                    pageToken=page_token,
                )
                .execute()
            )
            items.extend(resp.get("files", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return items

    def read_file_text(self, file_id: str, mime_type: str, max_chars: int) -> str | None:
        """Read file content as text, capped at max_chars."""
        try:
            if mime_type == "application/vnd.google-apps.folder":
                return None

            if mime_type in EXPORT_MIME:
                data = (
                    self._service.files()
                    .export(fileId=file_id, mimeType=EXPORT_MIME[mime_type])
                    .execute()
                )
                if isinstance(data, bytes):
                    text = data.decode("utf-8", errors="replace")
                else:
                    text = str(data)
                return text[:max_chars]

            if mime_type == "application/pdf":
                data = self._service.files().get_media(fileId=file_id).execute()
                return self._extract_pdf_text(data, max_chars)

            if mime_type.startswith(READABLE_MIME_PREFIXES) or mime_type in (
                "application/octet-stream",
            ):
                data = self._service.files().get_media(fileId=file_id).execute()
                text = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)
                return text[:max_chars]

            return None
        except Exception as exc:
            logger.warning("drive: could not read %s (%s): %s", file_id, mime_type, exc)
            return None

    @staticmethod
    def _extract_pdf_text(data: bytes, max_chars: int) -> str | None:
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            parts = []
            for page in reader.pages[:20]:
                parts.append(page.extract_text() or "")
                if sum(len(p) for p in parts) >= max_chars:
                    break
            return "".join(parts)[:max_chars]
        except Exception as exc:
            logger.warning("drive: PDF extract failed: %s", exc)
            return f"[PDF — {len(data)} bytes, text extraction unavailable]"

    def find_or_create_folder(self, name: str, parent_id: str) -> str:
        q = (
            f"name='{name}' and '{parent_id}' in parents "
            f"and mimeType='application/vnd.google-apps.folder' and trashed=false"
        )
        resp = (
            self._service.files()
            .list(q=q, fields="files(id)", pageSize=1)
            .execute()
        )
        files = resp.get("files", [])
        if files:
            return files[0]["id"]

        meta = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        created = self._service.files().create(body=meta, fields="id").execute()
        return created["id"]

    def upload_file(
        self,
        local_path: str,
        parent_id: str,
        drive_name: str | None = None,
    ) -> str:
        from googleapiclient.http import MediaFileUpload

        path = Path(local_path)
        name = drive_name or path.name
        mime, _ = mimetypes.guess_type(str(path))
        mime = mime or "application/octet-stream"

        meta = {"name": name, "parents": [parent_id]}
        media = MediaFileUpload(str(path), mimetype=mime, resumable=True)
        created = (
            self._service.files()
            .create(body=meta, media_body=media, fields="id")
            .execute()
        )
        return created["id"]
