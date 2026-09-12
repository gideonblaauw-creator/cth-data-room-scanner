"""
app/review.py
Production HITL reviewer routes — load real scan findings, save locks to disk.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, abort, jsonify, request, send_from_directory

from redis import Redis
from rq.job import Job

from scanner.config import OUTPUT_DIR, REDIS_URL, REPO_ROOT
from scanner.findings_from_score import load_findings, normalize_findings_doc
from scanner.review_persistence import locks_path_for_job, merge_lock_records

logger = logging.getLogger(__name__)

review_bp = Blueprint(
    "review",
    __name__,
    static_folder=str(REPO_ROOT / "hitl" / "review"),
    static_url_path="/review/static",
)

redis_conn = Redis.from_url(REDIS_URL)
REVIEW_DIR = REPO_ROOT / "hitl" / "review"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _allowed_roots() -> tuple[Path, ...]:
    return (REPO_ROOT.resolve(), OUTPUT_DIR.resolve())


def _path_within_allowed_roots(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except (OSError, ValueError):
        return False
    for root in _allowed_roots():
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _resolve_path_param(path_param: str) -> Path | None:
    """Resolve ?path= under REPO_ROOT or OUTPUT_DIR only (no traversal)."""
    if not path_param or ".." in Path(path_param).parts:
        return None
    candidate = Path(path_param)
    if candidate.is_absolute():
        candidates = [candidate]
    else:
        candidates = [REPO_ROOT / candidate, OUTPUT_DIR / candidate]
    for c in candidates:
        try:
            resolved = c.resolve()
        except (OSError, ValueError):
            continue
        if _path_within_allowed_roots(resolved) and resolved.is_file():
            return resolved
    return None


def _becaps_demo_path() -> Path:
    """Generate BeCaps findings on the fly if missing."""
    from scanner.findings_from_score import (
        findings_from_score,
        findings_output_path,
        save_findings,
    )
    from scanner.score_runner import load_becaps_fixture

    scoring = load_becaps_fixture()
    scan_date = scoring["company"]["scan_date"]
    out = findings_output_path("becaps-demo", scan_date, OUTPUT_DIR)
    if not out.exists():
        doc = findings_from_score(scoring, source="dry_run", run_id="becaps-demo")
        save_findings(doc, out)
    return out


def _demo_alias_path(job_id: str) -> Path | None:
    aliases = {
        "demo": REPO_ROOT / "out" / "findings.json",
        "becaps": _becaps_demo_path(),
    }
    path = aliases.get(job_id)
    if path and path.exists():
        return path
    return None


def _resolve_findings_path(job_id: str) -> Path | None:
    """Resolve findings file from ?path=, demo aliases, or RQ job result."""
    path_param = request.args.get("path")
    if path_param is not None:
        resolved = _resolve_path_param(path_param)
        return resolved  # invalid explicit path → None (no alias fallback)

    alias = _demo_alias_path(job_id)
    if alias:
        return alias

    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        return None

    if not job.is_finished:
        return None

    result = job.result
    if isinstance(result, dict) and result.get("findings_path"):
        p = Path(result["findings_path"])
        if p.exists() and _path_within_allowed_roots(p):
            return p

    if isinstance(result, dict):
        slug = result.get("slug")
        scan_date = result.get("scan_date")
        if slug and scan_date:
            month = scan_date[:7]
            candidate = OUTPUT_DIR / f"{slug}-{month}.findings.json"
            if candidate.exists():
                return candidate

    return None


def _locks_path_for_job(job_id: str) -> Path:
    return locks_path_for_job(job_id, OUTPUT_DIR)


@review_bp.route("/review")
def review_index():
    """Review landing — UI loads job_id or path from query string."""
    return send_from_directory(REVIEW_DIR, "index.html")


@review_bp.route("/review/<job_id>")
def review_job(job_id: str):
    """Production reviewer UI for a scan job."""
    return send_from_directory(REVIEW_DIR, "index.html")


@review_bp.route("/api/review/<job_id>/findings")
def api_findings(job_id: str):
    findings_path = _resolve_findings_path(job_id)
    if not findings_path or not findings_path.exists():
        abort(404, description="Findings not found for this job")

    doc = load_findings(findings_path)
    doc["findings_path"] = str(findings_path)
    doc["job_id"] = job_id
    return jsonify(doc)


@review_bp.route("/api/review/<job_id>/locks", methods=["GET"])
def api_get_locks(job_id: str):
    if not _resolve_findings_path(job_id):
        abort(404, description="Findings not found")
    locks_path = _locks_path_for_job(job_id)
    if not locks_path.exists():
        return jsonify({
            "version": 1,
            "run_id": job_id,
            "locks": [],
            "path": str(locks_path),
            "job_id": job_id,
        })
    data = json.loads(locks_path.read_text(encoding="utf-8"))
    data.setdefault("path", str(locks_path))
    data.setdefault("job_id", job_id)
    return jsonify(data)


@review_bp.route("/api/review/<job_id>/locks", methods=["POST"])
def api_save_locks(job_id: str):
    findings_path = _resolve_findings_path(job_id)
    if not findings_path:
        abort(404, description="Findings not found")

    payload = request.get_json(silent=True)
    if not payload:
        abort(400, description="JSON body required")

    errors = _validate_locks_payload(payload)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400

    locks_path = _locks_path_for_job(job_id)
    locks_path.parent.mkdir(parents=True, exist_ok=True)
    payload.setdefault("saved_at", _now_iso())
    payload.setdefault("findings_path", str(findings_path))
    payload.setdefault("job_id", job_id)
    payload["path"] = str(locks_path)
    locks_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.info("review: autosaved locks → %s (%d records)", locks_path, len(payload.get("locks", [])))
    return jsonify({"ok": True, "path": str(locks_path), "lock_count": len(payload.get("locks", []))})


@review_bp.route("/api/review/<job_id>/locks/merge", methods=["POST"])
def api_merge_locks(job_id: str):
    """Merge server locks with client local locks; server wins ties on locked_at."""
    if not _resolve_findings_path(job_id):
        abort(404, description="Findings not found")

    body = request.get_json(silent=True) or {}
    local_locks = body.get("locks") or []
    if not isinstance(local_locks, list):
        abort(400, description="locks must be an array")

    locks_path = _locks_path_for_job(job_id)
    server_locks: list[dict] = []
    server_doc: dict = {}
    if locks_path.exists():
        server_doc = json.loads(locks_path.read_text(encoding="utf-8"))
        server_locks = server_doc.get("locks") or []

    merged, conflicts = merge_lock_records(server_locks, local_locks, prefer="server")
    doc = {
        "version": 1,
        "run_id": body.get("run_id") or server_doc.get("run_id") or job_id,
        "company": body.get("company") or server_doc.get("company") or "",
        "quiz_passed": body.get("quiz_passed", server_doc.get("quiz_passed", True)),
        "quiz_source": "production-review",
        "locked_at": _now_iso(),
        "reviewer": server_doc.get("reviewer"),
        "run_link": body.get("run_link") or server_doc.get("run_link"),
        "findings_path": str(_resolve_findings_path(job_id)),
        "job_id": job_id,
        "locks": merged,
        "merge_conflicts": conflicts,
        "saved_at": _now_iso(),
        "path": str(locks_path),
    }
    if merged:
        locks_path.parent.mkdir(parents=True, exist_ok=True)
        locks_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return jsonify({
        "ok": True,
        "path": str(locks_path),
        "locks": merged,
        "conflicts": conflicts,
        "lock_count": len(merged),
    })


def _validate_locks_payload(payload: dict) -> list[str]:
    errors: list[str] = []
    if payload.get("version") != 1:
        errors.append("version must be 1")
    locks = payload.get("locks")
    if not isinstance(locks, list):
        errors.append("locks must be an array")
        return errors

    for i, lock in enumerate(locks):
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
                errors.append(f"locks[{i}] missing {key}")
        if lock.get("human_decision") not in {"agree", "override", "defer"}:
            errors.append(f"locks[{i}] invalid human_decision")
        rationale = lock.get("rationale", "")
        if isinstance(rationale, str) and len(rationale) < 8:
            errors.append(f"locks[{i}] rationale too short (min 8 chars)")
        fid = lock.get("finding_id", "")
        if isinstance(fid, str) and not (fid.startswith("S") or fid.startswith("F")):
            errors.append(f"locks[{i}] finding_id must start with S or F")
    return errors


def normalize_fixture_file(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return normalize_findings_doc(raw)
