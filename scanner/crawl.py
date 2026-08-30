"""
scanner/crawl.py
Crawls a Google Drive folder recursively and returns a structured tree.

Uses Google Drive API (service account). Respects existing DRIVE_TREE_SCHEMA.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from scanner.config import assert_not_becaps_folder
from scanner.drive_client import DriveClient

logger = logging.getLogger(__name__)

DRIVE_TREE_SCHEMA = {
    "folder_id": "string",
    "folder_name": "string",
    "crawled_at": "ISO datetime",
    "total_files": "int",
    "total_folders": "int",
    "empty_folders": ["list of folder names that returned no files"],
    "items": [
        {
            "id": "string",
            "name": "string",
            "type": "folder | document | spreadsheet | presentation | pdf | other",
            "size_bytes": "int | null",
            "content_snippet": "string (first 4000 chars of readable content) | null",
            "children": ["...recursive same schema for folders"],
        }
    ],
}

PILLAR_FOLDER_SIGNALS = {
    "team": ["equipo", "team", "cv", "currículum", "founders", "advisors"],
    "financials": [
        "finanzas", "financials", "financial", "presupuesto", "budget", "proyecciones"
    ],
    "legal": ["legal", "contratos", "contracts", "ip", "patentes", "cap table"],
    "impact": ["impacto", "impact", "esg", "asg", "sostenibilidad"],
    "market": ["mercado", "market", "competencia", "competitors"],
    "traction": ["clientes", "clients", "pipeline", "ventas", "sales", "contratos"],
    "investor": ["inversores", "investors", "deck", "pitch", "one-pager"],
}

PRIORITY_FILE_KEYWORDS = [
    "one-pager", "onepager", "pitch", "deck", "inversores",
    "cv", "currículum", "resume", "equipo", "team",
    "cap table", "safe", "contrato", "contract",
    "financial", "finanzas", "proyección", "projection",
    "impacto", "impact", "cif", "validation",
    "pipeline", "clientes", "market",
]

MAX_CONTENT_CHARS_PER_FILE = 4000
MAX_FILES_TO_READ_FULLY = 20

FOLDER_MIME = "application/vnd.google-apps.folder"


def extract_folder_id(url_or_id: str) -> str:
    """Extract Google Drive folder ID from URL or raw ID."""
    text = url_or_id.strip()
    match = re.search(r"/folders/([a-zA-Z0-9_-]+)", text)
    if match:
        return match.group(1)
    match = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", text)
    if match:
        return match.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{10,}", text):
        return text
    raise ValueError(f"Cannot extract Drive folder ID from: {url_or_id!r}")


def _mime_to_type(mime: str, name: str) -> str:
    if mime == FOLDER_MIME:
        return "folder"
    if mime == "application/vnd.google-apps.document":
        return "document"
    if mime == "application/vnd.google-apps.spreadsheet":
        return "spreadsheet"
    if mime == "application/vnd.google-apps.presentation":
        return "presentation"
    if mime == "application/pdf" or name.lower().endswith(".pdf"):
        return "pdf"
    return "other"


def _priority_score(name: str) -> int:
    lower = name.lower()
    for i, kw in enumerate(PRIORITY_FILE_KEYWORDS):
        if kw in lower:
            return len(PRIORITY_FILE_KEYWORDS) - i
    return 0


def crawl_folder(
    folder_id: str,
    drive: DriveClient | None = None,
    *,
    read_contents: bool = True,
) -> dict[str, Any]:
    """
    Recursively crawl a Drive folder and return DRIVE_TREE_SCHEMA-shaped dict.
    Reads up to MAX_FILES_TO_READ_FULLY files (MAX_CONTENT_CHARS_PER_FILE each).
    """
    assert_not_becaps_folder(folder_id, "crawl for write")

    client = drive or DriveClient()
    meta = client.get_file_metadata(folder_id)
    folder_name = meta.get("name", folder_id)

    # Collect all file nodes flat first for priority sorting
    file_nodes: list[dict[str, Any]] = []
    empty_folders: list[str] = []
    total_files = 0
    total_folders = 0

    def walk(parent_id: str) -> list[dict[str, Any]]:
        nonlocal total_files, total_folders
        children_meta = client.list_children(parent_id)
        if not children_meta:
            parent_meta = client.get_file_metadata(parent_id)
            if parent_meta.get("mimeType") == FOLDER_MIME and parent_id != folder_id:
                empty_folders.append(parent_meta.get("name", parent_id))

        items: list[dict[str, Any]] = []
        for child in sorted(children_meta, key=lambda c: c.get("name", "").lower()):
            mime = child.get("mimeType", "")
            name = child.get("name", "")
            cid = child["id"]
            ftype = _mime_to_type(mime, name)

            if ftype == "folder":
                total_folders += 1
                sub = walk(cid)
                items.append({
                    "id": cid,
                    "name": name,
                    "type": "folder",
                    "size_bytes": None,
                    "content_snippet": None,
                    "children": sub,
                })
            else:
                total_files += 1
                node = {
                    "id": cid,
                    "name": name,
                    "type": ftype,
                    "size_bytes": int(child.get("size", 0) or 0),
                    "content_snippet": None,
                    "children": [],
                    "_mime": mime,
                    "_priority": _priority_score(name),
                }
                file_nodes.append(node)
                items.append(node)
        return items

    items = walk(folder_id)

    # Read content for top-priority files
    if read_contents and file_nodes:
        file_nodes.sort(key=lambda n: (-n["_priority"], n["name"].lower()))
        for node in file_nodes[:MAX_FILES_TO_READ_FULLY]:
            snippet = client.read_file_text(
                node["id"],
                node.pop("_mime"),
                MAX_CONTENT_CHARS_PER_FILE,
            )
            node["content_snippet"] = snippet
        for node in file_nodes[MAX_FILES_TO_READ_FULLY:]:
            node.pop("_mime", None)
            node.pop("_priority", None)
        for node in file_nodes[:MAX_FILES_TO_READ_FULLY]:
            node.pop("_priority", None)

    def strip_internal(nodes: list[dict]) -> list[dict]:
        clean = []
        for n in nodes:
            entry = {k: v for k, v in n.items() if not k.startswith("_")}
            if entry.get("type") == "folder":
                entry["children"] = strip_internal(entry.get("children", []))
            clean.append(entry)
        return clean

    return {
        "folder_id": folder_id,
        "folder_name": folder_name,
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "total_files": total_files,
        "total_folders": total_folders,
        "empty_folders": empty_folders,
        "items": strip_internal(items),
    }
