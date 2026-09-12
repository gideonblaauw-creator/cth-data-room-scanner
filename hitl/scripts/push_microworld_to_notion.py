#!/usr/bin/env python3
"""
Push microworld lock decisions to the CleantechHUB Notion Decisions database.

Reads hitl/out/microworld-locks.json (or --locks path) and upserts rows via the
Notion API. Token must come from environment / Infisical — never from the browser.

Env vars (names only):
  NOTION_API_TOKEN          — Notion integration token
  NOTION_DECISIONS_DATA_SOURCE_ID — defaults to CleantechHUB collection id

Usage:
  python hitl/scripts/push_microworld_to_notion.py
  python hitl/scripts/push_microworld_to_notion.py --dry-run
  python hitl/scripts/push_microworld_to_notion.py --locks hitl/out/microworld-locks.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_LOCKS = ROOT / "hitl" / "out" / "microworld-locks.json"
DEFAULT_DATA_SOURCE = "5f2cca6c-867a-4884-a365-0f693c0dbf27"
NOTION_VERSION = "2022-06-28"

HUMAN_DECISIONS = {"agree", "override", "defer"}
STATUSES = {"pending", "reviewed", "waived", "blocked"}


def load_locks(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Locks file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_locks(data)
    return data


def validate_locks(data: dict[str, Any]) -> None:
    required_top = ["version", "run_id", "company", "quiz_passed", "locked_at", "locks"]
    for key in required_top:
        if key not in data:
            raise ValueError(f"Missing required field: {key}")
    if data["version"] != 1:
        raise ValueError(f"Unsupported locks version: {data['version']}")
    if not data["locks"]:
        raise ValueError("locks array must not be empty")
    for lock in data["locks"]:
        for key in (
            "finding_id",
            "fixture_path",
            "agent_suggestion",
            "human_decision",
            "rationale",
            "status",
            "locked_at",
        ):
            if key not in lock:
                raise ValueError(f"Lock {lock.get('finding_id', '?')} missing {key}")
        if lock["human_decision"] not in HUMAN_DECISIONS:
            raise ValueError(f"Invalid human_decision: {lock['human_decision']}")
        if lock["status"] not in STATUSES:
            raise ValueError(f"Invalid status: {lock['status']}")
        if len(lock["rationale"].strip()) < 8:
            raise ValueError(
                f"Rationale too short for {lock['finding_id']} (min 8 chars)"
            )


def _notion_request(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Notion API {exc.code}: {detail}") from exc


def query_existing_pages(
    token: str, data_source_id: str, run_id: str
) -> dict[str, str]:
    """Return mapping finding_id -> page_id for this run."""
    url = f"https://api.notion.com/v1/data_sources/{data_source_id}/query"
    payload = {
        "filter": {
            "property": "Run link",
            "url": {"contains": run_id},
        }
    }
    result = _notion_request("POST", url, token, payload)
    mapping: dict[str, str] = {}
    for page in result.get("results", []):
        props = page.get("properties", {})
        title_prop = props.get("Finding ID") or props.get("Name") or {}
        title_parts = title_prop.get("title", [])
        if title_parts:
            finding_id = title_parts[0].get("plain_text", "")
            if finding_id:
                mapping[finding_id] = page["id"]
    return mapping


def build_page_properties(lock: dict[str, Any], locks_doc: dict[str, Any]) -> dict[str, Any]:
    agent_line = lock.get("agent_label")
    if agent_line:
        agent_suggestion = f"{agent_line} → {lock['agent_suggestion']}"
    else:
        agent_suggestion = lock["agent_suggestion"]

    run_link = locks_doc.get("run_link") or f"hitl/out/microworld-locks.json#{lock['finding_id']}"

    props: dict[str, Any] = {
        "Finding ID": {
            "title": [{"type": "text", "text": {"content": lock["finding_id"]}}],
        },
        "Fixture path": {
            "rich_text": [{"type": "text", "text": {"content": lock["fixture_path"]}}],
        },
        "Agent suggestion": {
            "rich_text": [{"type": "text", "text": {"content": agent_suggestion}}],
        },
        "Human decision": {"select": {"name": lock["human_decision"]}},
        "Rationale": {
            "rich_text": [{"type": "text", "text": {"content": lock["rationale"]}}],
        },
        "Quiz passed": {"checkbox": bool(locks_doc.get("quiz_passed"))},
        "Status": {"select": {"name": lock["status"]}},
        "Run link": {"url": run_link if run_link.startswith("http") else None},
    }
    reviewer = locks_doc.get("reviewer")
    if reviewer:
        props["Reviewer"] = {
            "rich_text": [{"type": "text", "text": {"content": reviewer}}],
        }
    return props


def upsert_lock(
    token: str,
    data_source_id: str,
    lock: dict[str, Any],
    locks_doc: dict[str, Any],
    existing: dict[str, str],
    dry_run: bool,
) -> str:
    finding_id = lock["finding_id"]
    properties = build_page_properties(lock, locks_doc)

    if dry_run:
        action = "update" if finding_id in existing else "create"
        return f"[dry-run] {action} {finding_id}"

    if finding_id in existing:
        page_id = existing[finding_id]
        _notion_request(
            "PATCH",
            f"https://api.notion.com/v1/pages/{page_id}",
            token,
            {"properties": properties},
        )
        return f"updated {finding_id}"

    payload = {
        "parent": {"type": "data_source_id", "data_source_id": data_source_id},
        "properties": properties,
    }
    _notion_request("POST", "https://api.notion.com/v1/pages", token, payload)
    return f"created {finding_id}"


def render_paste_pack(locks_doc: dict[str, Any]) -> str:
    lines = [
        "# Notion paste pack — microworld locks",
        "",
        f"Run: `{locks_doc['run_id']}` · Quiz passed: {locks_doc['quiz_passed']}",
        "",
        "| Finding ID | Fixture | Decision | Rationale | Status |",
        "|------------|---------|----------|-----------|--------|",
    ]
    for lock in locks_doc["locks"]:
        rationale = lock["rationale"].replace("|", "\\|")[:80]
        lines.append(
            f"| {lock['finding_id']} | {lock['fixture_path']} | "
            f"{lock['human_decision']} | {rationale} | {lock['status']} |"
        )
    lines.extend(
        [
            "",
            "Paste into Decisions DB:",
            "https://app.notion.com/p/bb52cfa45b6744e59983528480fbab4b",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Push microworld locks to Notion")
    parser.add_argument(
        "--locks",
        type=Path,
        default=DEFAULT_LOCKS,
        help="Path to microworld-locks.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print actions without calling Notion",
    )
    parser.add_argument(
        "--paste-pack",
        action="store_true",
        help="Print markdown paste pack for manual Notion entry",
    )
    args = parser.parse_args()

    try:
        locks_doc = load_locks(args.locks)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.paste_pack:
        print(render_paste_pack(locks_doc))
        return 0

    token = os.environ.get("NOTION_API_TOKEN") or os.environ.get("NOTION_TOKEN")
    data_source_id = (
        os.environ.get("NOTION_DECISIONS_DATA_SOURCE_ID", DEFAULT_DATA_SOURCE)
        .replace("collection://", "")
    )

    if args.dry_run:
        print(f"Validated {len(locks_doc['locks'])} locks for run {locks_doc['run_id']}")
        for lock in locks_doc["locks"]:
            print(
                f"  [dry-run] upsert {lock['finding_id']}: "
                f"{lock['human_decision']} → {lock['status']}"
            )
        return 0

    if not token:
        print(
            "ERROR: NOTION_API_TOKEN not set. Use --dry-run or --paste-pack for offline flow.",
            file=sys.stderr,
        )
        return 1

    try:
        existing = query_existing_pages(token, data_source_id, locks_doc["run_id"])
    except RuntimeError as exc:
        print(f"WARN: could not query existing pages ({exc}); will create new rows")

        existing = {}

    results = []
    for lock in locks_doc["locks"]:
        try:
            results.append(
                upsert_lock(
                    token, data_source_id, lock, locks_doc, existing, dry_run=False
                )
            )
        except RuntimeError as exc:
            print(f"ERROR on {lock['finding_id']}: {exc}", file=sys.stderr)
            return 1

    print(f"Pushed {len(results)} decisions for run {locks_doc['run_id']}:")
    for line in results:
        print(f"  ✓ {line}")
    print(
        "\nDecisions DB: https://app.notion.com/p/bb52cfa45b6744e59983528480fbab4b"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
