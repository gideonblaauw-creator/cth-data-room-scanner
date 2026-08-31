"""
app/main.py
Thin HTTP form for submitting data-room scans.
Binds to 127.0.0.1 by default — Caddy terminates TLS at the edge.

Lane A split: this Flask app handles scan jobs (POST URL+metadata only).
The public React shell in web/ calls /api/* — never crawls Drive in the browser.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template_string, request, send_from_directory, url_for
from redis import Redis
from rq import Queue
from rq.job import Job

from scanner.config import APP_HOST, APP_PORT, OUTPUT_DIR, REDIS_URL, RQ_QUEUE_NAME

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
redis_conn = Redis.from_url(REDIS_URL)
queue = Queue(RQ_QUEUE_NAME, connection=redis_conn)

CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

FORM_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CTH Data Room Scanner</title>
  <style>
    :root {
      --cth-deep: #0C498A;
      --cth-cyan: #B2EEFA;
      --cth-green-light: #9DC384;
      --cth-green: #669348;
      --cth-blue: #69B5FA;
      --cth-light: #E8F7FC;
      --border: #B2EEFA;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Open Sans', 'PT Sans', sans-serif;
      background: var(--cth-light);
      color: #0C498A;
      line-height: 1.5;
      padding: 40px 20px;
    }
    .container { max-width: 560px; margin: 0 auto; }
    h1 { font-size: 1.5rem; color: #fff; background: var(--cth-deep); padding: 12px 16px;
      border-radius: 8px; margin-bottom: 4px; }
    .subtitle { color: #669348; font-size: 0.9rem; margin-bottom: 28px; font-style: italic; }
    label { display: block; font-weight: 600; font-size: 0.85rem; margin-bottom: 6px; color: var(--cth-deep); }
    input, select, textarea {
      width: 100%; padding: 10px 12px; border: 1px solid var(--border);
      border-radius: 8px; font-size: 0.95rem; margin-bottom: 16px;
      font-family: inherit;
    }
    textarea { min-height: 80px; resize: vertical; }
    button {
      background: var(--cth-green); color: #fff; border: none;
      padding: 12px 24px; border-radius: 8px; font-size: 1rem;
      font-weight: 600; cursor: pointer; width: 100%;
      font-family: inherit;
    }
    button:hover { background: var(--cth-deep); }
    .status { margin-top: 24px; padding: 16px; border-radius: 8px; background: #fff;
      border: 1px solid var(--border); }
    .status h2 { font-size: 1rem; margin-bottom: 8px; color: var(--cth-deep); }
    .status pre { font-size: 0.85rem; white-space: pre-wrap; }
    .badge { display: inline-block; padding: 2px 10px; border-radius: 12px;
      font-size: 0.8rem; font-weight: 600; }
    .badge-queued { background: var(--cth-cyan); color: var(--cth-deep); }
    .badge-started { background: var(--cth-blue); color: var(--cth-deep); }
    .badge-finished { background: var(--cth-green-light); color: var(--cth-deep); }
    .badge-failed { background: #FEE2E2; color: #991B1B; }
    footer { margin-top: 40px; text-align: center; font-size: 0.75rem; color: #669348; }
  </style>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&family=PT+Sans:wght@400;700&display=swap" rel="stylesheet">
</head>
<body>
  <div class="container">
    <h1>CTH Data Room Scanner</h1>
    <p class="subtitle">Inspira. Actúa. Transforma.</p>

    <form method="POST" action="/scan">
      <label for="drive_url">Enlace carpeta Google Drive</label>
      <input type="url" id="drive_url" name="drive_url" required
        placeholder="https://drive.google.com/drive/folders/...">

      <label for="company_name">Nombre de la empresa</label>
      <input type="text" id="company_name" name="company_name" required>

      <label for="lang">Idioma del informe</label>
      <select id="lang" name="lang">
        <option value="es" selected>Español</option>
        <option value="en">English</option>
      </select>

      <label for="context_notes">Contexto adicional (opcional)</label>
      <textarea id="context_notes" name="context_notes"
        placeholder="Ronda, etapa, notas del founder..."></textarea>

      <button type="submit">Iniciar escaneo</button>
    </form>

    {% if job_id %}
    <div class="status">
      <h2>Estado del escaneo</h2>
      <p>Job ID: <code>{{ job_id }}</code>
        <span class="badge badge-{{ status }}">{{ status }}</span>
      </p>
      {% if result %}
      <pre>{{ result }}</pre>
      {% endif %}
      {% if error %}
      <pre style="color:#991B1B">{{ error }}</pre>
      {% endif %}
      <p style="margin-top:12px"><a href="/status/{{ job_id }}">Actualizar estado</a></p>
    </div>
    {% endif %}

    <footer>CLEANTECHHUB INTERNATIONAL S.L.</footer>
  </div>
</body>
</html>"""


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    if origin and origin.rstrip("/") in {o.rstrip("/") for o in CORS_ORIGINS}:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def _enqueue_scan(drive_url: str, company_name: str, lang: str, context_notes: str) -> str:
    from app.tasks import run_scan_job

    job = queue.enqueue(
        run_scan_job,
        drive_url,
        company_name,
        lang,
        context_notes,
        job_timeout="30m",
        result_ttl=86400,
        job_id=str(uuid.uuid4()),
    )
    return job.id


def _fetch_job_status(job_id: str) -> dict:
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        return {
            "job_id": job_id,
            "status": "failed",
            "error": "Job not found",
            "result": None,
        }

    status = job.get_status()
    result = None
    error = None

    if job.is_finished:
        result = job.result
    elif job.is_failed:
        error = str(job.exc_info or job.meta.get("error", "Unknown error"))

    return {
        "job_id": job_id,
        "status": status,
        "result": result,
        "error": error,
    }


@app.route("/", methods=["GET"])
def index():
    return render_template_string(FORM_HTML)


@app.route("/scan", methods=["POST"])
def submit_scan():
    drive_url = request.form.get("drive_url", "").strip()
    company_name = request.form.get("company_name", "").strip()
    lang = request.form.get("lang", "es")
    context_notes = request.form.get("context_notes", "").strip()

    if not drive_url or not company_name:
        return redirect(url_for("index"))

    job_id = _enqueue_scan(drive_url, company_name, lang, context_notes)
    return redirect(url_for("job_status", job_id=job_id))


@app.route("/status/<job_id>")
def job_status(job_id: str):
    data = _fetch_job_status(job_id)
    result = data.get("result")
    if isinstance(result, dict):
        result = result.get("summary", str(result))

    return render_template_string(
        FORM_HTML,
        job_id=data["job_id"],
        status=data["status"],
        result=result,
        error=data.get("error"),
    )


@app.route("/api/scan", methods=["POST", "OPTIONS"])
def api_submit_scan():
    if request.method == "OPTIONS":
        return "", 204

    payload = request.get_json(silent=True) or {}
    drive_url = str(payload.get("drive_url", "")).strip()
    company_name = str(payload.get("company_name", "")).strip()
    lang = str(payload.get("lang", "es")).strip() or "es"
    context_notes = str(payload.get("context_notes", "")).strip()

    if not drive_url or not company_name:
        return jsonify({"error": "drive_url and company_name are required"}), 400

    job_id = _enqueue_scan(drive_url, company_name, lang, context_notes)
    return jsonify({"job_id": job_id}), 202


@app.route("/api/status/<job_id>", methods=["GET"])
def api_job_status(job_id: str):
    data = _fetch_job_status(job_id)
    return jsonify(data)


@app.route("/reports/<path:filename>")
def serve_report(filename: str):
    """Serve local report files for dev/preview (output dir only)."""
    output_root = Path(OUTPUT_DIR).resolve()
    file_path = (output_root / filename).resolve()
    if not str(file_path).startswith(str(output_root)):
        return jsonify({"error": "Invalid path"}), 403
    if not file_path.is_file():
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(output_root, filename)


@app.route("/health")
def health():
    try:
        redis_conn.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    return {"status": "ok" if redis_ok else "degraded", "redis": redis_ok}


def main():
    app.run(host=APP_HOST, port=APP_PORT, debug=False)


if __name__ == "__main__":
    main()
