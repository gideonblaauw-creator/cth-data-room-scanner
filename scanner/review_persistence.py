"""
scanner/review_persistence.py
Server-side lock file paths and merge helpers for production reviewer persistence.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def locks_path_for_job(job_id: str, output_dir: Path) -> Path:
    """Canonical SoT: output/{job_id}-review-locks.json"""
    safe = job_id.replace("/", "_").replace("\\", "_")
    return output_dir / f"{safe}-review-locks.json"


def _parse_locked_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def merge_lock_records(
    server_locks: list[dict],
    local_locks: list[dict],
    *,
    prefer: str = "server",
) -> tuple[list[dict], list[str]]:
    """
    Merge lock records by finding_id.

    Newer locked_at wins; on tie, prefer server (or local if prefer='local').
    Returns (merged_locks sorted by finding_id, conflict finding_ids).
    """
    merged: dict[str, dict] = {}
    conflicts: list[str] = []

    def consider(lock: dict, source: str) -> None:
        fid = lock.get("finding_id")
        if not fid:
            return
        existing = merged.get(fid)
        if existing is None:
            merged[fid] = dict(lock)
            merged[fid]["_source"] = source
            return

        ex_at = _parse_locked_at(existing.get("locked_at"))
        new_at = _parse_locked_at(lock.get("locked_at"))
        if ex_at and new_at:
            if new_at > ex_at:
                merged[fid] = dict(lock)
                merged[fid]["_source"] = source
            elif new_at < ex_at:
                return
            else:
                conflicts.append(fid)
                if prefer == "local" and source == "local":
                    merged[fid] = dict(lock)
                    merged[fid]["_source"] = source
                elif prefer == "server" and source == "server":
                    merged[fid] = dict(lock)
                    merged[fid]["_source"] = source
        elif source == prefer:
            merged[fid] = dict(lock)
            merged[fid]["_source"] = source

    for lock in server_locks:
        consider(lock, "server")
    for lock in local_locks:
        consider(lock, "local")

    result = []
    for fid in sorted(merged.keys()):
        item = dict(merged[fid])
        item.pop("_source", None)
        result.append(item)
    return result, conflicts
