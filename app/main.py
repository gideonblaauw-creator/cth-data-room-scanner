"""
app/main.py
Thin HTTP form for submitting data-room scans.
Binds to 127.0.0.1 by default — Caddy terminates TLS at the edge.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, url_for
from redis import Redis
from rq import Queue
from rq.job import Job

from app.review import review_bp
from scanner.config import APP_HOST, APP_PORT, REDIS_URL, RQ_QUEUE_NAME

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.register_blueprint(review_bp)
redis_conn = Redis.from_url(REDIS_URL)
queue = Queue(RQ_QUEUE_NAME, connection=redis_conn)

FORM_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CTH Data Room Scanner</title>
  <style>
    :root {
      --cth-primary: #2D6A4F;
      --cth-dark: #1B4332;
      --cth-light: #f8faf9;
      --border: #e2e8f0;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: "Segoe UI", Inter, -apple-system, sans-serif;
      background: var(--cth-light);
      color: #1a1a1a;
      line-height: 1.5;
      padding: 40px 20px;
    }
    .container { max-width: 560px; margin: 0 auto; }
    h1 { font-size: 1.5rem; color: var(--cth-dark); margin-bottom: 4px; }
    .subtitle { color: #718096; font-size: 0.9rem; margin-bottom: 28px; }
    label { display: block; font-weight: 600; font-size: 0.85rem; margin-bottom: 6px; }
    input, select, textarea {
      width: 100%; padding: 10px 12px; border: 1px solid var(--border);
      border-radius: 8px; font-size: 0.95rem; margin-bottom: 16px;
    }
    textarea { min-height: 80px; resize: vertical; }
    button {
      background: var(--cth-primary); color: #fff; border: none;
      padding: 12px 24px; border-radius: 8px; font-size: 1rem;
      font-weight: 600; cursor: pointer; width: 100%;
    }
    button:hover { background: var(--cth-dark); }
    .status { margin-top: 24px; padding: 16px; border-radius: 8px; background: #fff;
      border: 1px solid var(--border); }
    .status h2 { font-size: 1rem; margin-bottom: 8px; }
    .status pre { font-size: 0.85rem; white-space: pre-wrap; }
    .badge { display: inline-block; padding: 2px 10px; border-radius: 12px;
      font-size: 0.8rem; font-weight: 600; }
    .badge-queued { background: #FEF3C7; color: #92400E; }
    .badge-started { background: #DBEAFE; color: #1E40AF; }
    .badge-finished { background: #D8F3DC; color: #1B4332; }
    .badge-failed { background: #FEE2E2; color: #991B1B; }
    footer { margin-top: 40px; text-align: center; font-size: 0.75rem; color: #a0aec0; }
  </style>
</head>
<body>
  <div class="container">
    <h1>CTH Data Room Scanner</h1>
    <p class="subtitle">Informe de due diligence automatizado — HTML + PDF</p>

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
      {% if review_url %}
      <p style="margin-top:12px">
        <a href="{{ review_url }}" style="font-weight:600;color:var(--cth-primary)">Review findings →</a>
      </p>
      {% endif %}
      {% if error %}
      <pre style="color:#991B1B">{{ error }}</pre>
      {% endif %}
      <p style="margin-top:12px"><a href="/status/{{ job_id }}">Actualizar estado</a></p>
    </div>
    {% endif %}

    <footer>CTH Growth Services &middot; CLEANTECHHUB INTERNATIONAL S.L.</footer>
  </div>
</body>
</html>"""


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
    return redirect(url_for("job_status", job_id=job.id))


@app.route("/status/<job_id>")
def job_status(job_id: str):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        return render_template_string(
            FORM_HTML, job_id=job_id, status="failed", error="Job not found"
        )

    status = job.get_status()
    result = None
    error = None
    review_url = None

    if job.is_finished:
        job_result = job.result
        if isinstance(job_result, dict):
            result = job_result.get("summary", str(job_result))
            if job_result.get("findings_path"):
                review_url = url_for("review.review_job", job_id=job_id)
        else:
            result = str(job_result)
    elif job.is_failed:
        error = str(job.exc_info or job.meta.get("error", "Unknown error"))

    return render_template_string(
        FORM_HTML, job_id=job_id, status=status, result=result, error=error, review_url=review_url
    )


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
