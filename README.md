# CTH Data Room Scanner

Scans a startup's Google Drive data room and produces a branded due diligence report
(HTML + PDF) aligned to CTH's 8-pillar Growth Services framework.

## Who uses this

CTH team — Gideon, Jop, Brian (Kwakman).

Two modes:
- **Claude Code** — `/scan` slash command (in-session MCP, legacy workflow)
- **Web app** — React shell in `web/` + Flask API on `http://127.0.0.1:8080` with Redis-backed job queue (Lane A)

## Quick start (compose)

```bash
# 1. Clone and configure
git clone https://github.com/gideonblaauw-creator/cth-data-room-scanner.git
cd cth-data-room-scanner
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY and mount Google service account JSON

# 2. Place service account key (never commit)
mkdir -p secrets
cp /path/to/google-sa.json secrets/google-sa.json

# 3. Start stack
docker compose up --build

# 4. Open React shell (dev)
cd web && npm install && npm run dev
# → http://localhost:5173  (proxies /api to Flask :8080)

# Or open legacy Flask form directly:
open http://127.0.0.1:8080
```

Services:
| Service | Role |
|---------|------|
| `web` (compose) | Flask API on 127.0.0.1:8080 |
| `web/` (React) | Public CTH-branded shell — see `web/README.md` |
| `worker` | RQ worker — crawl, score, render, PDF, upload |
| `redis` | Job queue |

Caddy terminates TLS in production — the app binds to localhost only.

## Dry-run (no API keys)

```bash
pip install -r requirements.txt
playwright install chromium
python scripts/dry_run.py --company "TestCo"
```

Uses BeCaps 3.5 calibration fixture. Generates local HTML (+ PDF if Playwright installed).
No Drive crawl, no LLM call, no upload.

## Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## How a scan works

1. **Parse** — Drive folder URL/ID, company name, language
2. **Crawl** — recursive Drive folder (max 20 files × 4000 chars)
3. **Score** — LLM scores 8 pillars using `skills/cth-growth-services.md`
4. **Render** — inject JSON into `templates/report.html`
5. **PDF** — Playwright headless Chromium (WeasyPrint fallback)
6. **Upload** — HTML + PDF to shared Drive reports folder
7. **Summary** — job status in web UI

## Outputs

Local working copies (gitignored):
- `output/{slug}-{YYYY-MM}.html`
- `output/{slug}-{YYYY-MM}.pdf`

Shared Drive (team access):
- `CTH Growth Services / Reports / {YYYY-MM} / {slug} /`
  - `{slug}-{YYYY-MM}.html`
  - `{slug}-{YYYY-MM}.pdf`

Drive folder: `1RvuoSvbm6SvbdCWU06Wa7jyfEniPmzbP`

Reports are **never** published to public URLs. Private data rooms stay in Drive only.

## Configuration

All paths are env-driven — no hardcoded `/opt/cth-data-room-scanner`.

| Variable | Default | Purpose |
|----------|---------|---------|
| `OUTPUT_DIR` | `./output` | Local report output |
| `DRIVE_REPORTS_FOLDER_ID` | `1RvuoSvbm6SvbdCWU06Wa7jyfEniPmzbP` | Upload destination |
| `GOOGLE_APPLICATION_CREDENTIALS` | — | Service account JSON path |
| `ANTHROPIC_API_KEY` | — | LLM scoring |
| `REDIS_URL` | `redis://redis:6379/0` | Job queue |
| `SELLER_LEGAL_NAME` | `CLEANTECHHUB INTERNATIONAL S.L.` | Report footer |

### Secrets (SOPS+age)

For VPS deployment, encrypt `.env` with SOPS+age. Age key lives on the VPS only — never in git.

## Calibration reference

BeCaps (April 2026): 3.5/5 — GO Phase 1. Use as scoring benchmark.

| Field | Value |
|-------|-------|
| Drive folder | `1sg4TlFoP2_YVYmDdxuacC3Gs4kpB0Bd_` |
| Access | **READ-ONLY** — never write to this folder |

## Claude Code workflow (legacy)

```
/scan https://drive.google.com/drive/folders/FOLDER_ID
```

See `.claude/commands/scan.md` for the in-session flow.

## Architecture

```
┌──────────────┐     ┌──────────┐     ┌───────┐     ┌────────┐
│ React shell  │────▶│ Flask API│────▶│ Redis │────▶│ Worker │
│ web/ :5173   │     │ :8080    │     │  RQ   │     │        │
└──────────────┘     └──────────┘     └───────┘     └───┬────┘
                                                         │
                                          ┌──────────────┼──────────────┐
                                          ▼              ▼              ▼
                                    Drive API      Anthropic API   Playwright
                                    (crawl/upload)  (scoring)      (PDF)
```

DNS público para el shell React: **[PENDIENTE]** — no publicar en `reportes.cleantechhub.net`.

## Current team

- Gideon Blaauw — gideon.blaauw@cleantechhub.net
- Jop Blom — jop.blom@cleantechhub.net
- Brian Kwakman — brian.kwakman@behold.nl

## Status

| Component | Status |
|-----------|--------|
| `templates/report.html` + `scanner/render.py` | ✅ Runnable |
| `scanner/pdf.py` | ✅ Runnable |
| `scanner/crawl.py` | ✅ Drive API implementation |
| `scanner/upload.py` | ✅ Drive API implementation |
| `scanner/score_runner.py` + `scanner/runner.py` | ✅ Headless steps 1–7 |
| `app/main.py` + RQ worker | ✅ Flask API + queue + legacy form |
| `web/` React shell | ✅ CTH-branded Lane A UI |
| `compose.yml` | ✅ Redis + web + worker + Playwright |
| `scripts/dry_run.py` + `tests/` | ✅ Dry-run + pytest |
| Caddy TLS edge | [PENDIENTE] |
| CI pipeline | [PENDIENTE] |
| VPS deploy (Hands) | [PENDIENTE] |
