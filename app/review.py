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


def _resolve_findings_path(job_id: str) -> Path | None:
    """Resolve findings file from RQ job result or explicit path query."""
    path_param = request.args.get("path")
    if path_param:
        p = Path(path_param)
        if not p.is_absolute():
            p = REPO_ROOT / p
        if p.exists():
            return p

    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        return None

    if not job.is_finished:
        return None

    result = job.result
    if isinstance(result, dict) and result.get("findings_path"):
        p = Path(result["findings_path"])
        if p.exists():
            return p

    # Fallback: scan output dir for slug-date pattern stored in result
    if isinstance(result, dict):
        slug = result.get("slug")
        scan_date = result.get("scan_date")
        if slug and scan_date:
            month = scan_date[:7]
            candidate = OUTPUT_DIR / f"{slug}-{month}.findings.json"
            if candidate.exists():
                return candidate

    return None


def _locks_path_for_findings(findings_path: Path) -> Path:
    return findings_path.with_name(findings_path.stem + "-review-locks.json")


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
    if not findings_path:
        # Allow loading fixture/demo files by job_id alias
        aliases = {
            "demo": REPO_ROOT / "out" / "findings.json",
            "becaps": _becaps_demo_path(),
        }
        findings_path = aliases.get(job_id)
        if findings_path and not findings_path.exists():
            findings_path = None

    if not findings_path or not findings_path.exists():
        abort(404, description="Findings not found for this job")

    doc = load_findings(findings_path)
    doc["findings_path"] = str(findings_path)
    doc["job_id"] = job_id
    return jsonify(doc)


@review_bp.route("/api/review/<job_id>/locks", methods=["GET"])
def api_get_locks(job_id: str):
    findings_path = _resolve_findings_path(job_id)
    if not findings_path:
        abort(404, description="Findings not found")
    locks_path = _locks_path_for_findings(findings_path)
    if not locks_path.exists():
        return jsonify({"locks": [], "path": str(locks_path)})
    return jsonify(json.loads(locks_path.read_text(encoding="utf-8")))


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

    locks_path = _locks_path_for_findings(findings_path)
    locks_path.parent.mkdir(parents=True, exist_ok=True)
    payload.setdefault("saved_at", _now_iso())
    payload.setdefault("findings_path", str(findings_path))
    payload.setdefault("job_id", job_id)
    locks_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.info("review: saved locks → %s", locks_path)
    return jsonify({"ok": True, "path": str(locks_path)})


def _validate_locks_payload(payload: dict) -> list[str]:
    errors: list[str] = []
    if payload.get("version") != 1:
        errors.append("version must be 1")
    locks = payload.get("locks")
    if not isinstance(locks, list) or not locks:
        errors.append("locks must be a non-empty array")
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


def _becaps_demo_path() -> Path:
    """Generate BeCaps findings on the fly if missing."""
    from scanner.findings_from_score import findings_from_score, save_findings, findings_output_path
    from scanner.score_runner import load_becaps_fixture

    out = findings_output_path("becaps-demo", "2026-09-12", OUTPUT_DIR)
    if not out.exists():
        scoring = load_becaps_fixture()
        doc = findings_from_score(scoring, source="dry_run", run_id="becaps-demo")
        save_findings(doc, out)
    return out


def normalize_fixture_file(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return normalize_findings_doc(raw)
