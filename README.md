# CTH Data Room Scanner

Scans a startup's Google Drive data room and produces a branded due diligence report
(HTML + PDF) aligned to CTH's 8-pillar Growth Services framework.

## Who uses this

CTH team — Gideon, Jop, Brian (Kwakman).

Two modes:
- **Claude Code** — `/scan` slash command (in-session MCP, legacy workflow)
- **Web app** — form at `http://127.0.0.1:8080` with Redis-backed job queue (Lane A)

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

# 4. Open form
open http://127.0.0.1:8080
```

Services:
| Service | Role |
|---------|------|
| `web` | Flask form on 127.0.0.1:8080 |
| `worker` | RQ worker — crawl, score, render, PDF, upload |
| `redis` | Job queue |

Caddy terminates TLS in production — the app binds to localhost only.

## HITL demo (synthetic fixtures, no API keys)

First human-in-the-loop workflow for Dataroom Reviewer — **synthetic VertiGreen fixture only**, no real client datarooms or secrets.

```bash
make hitl-demo
```

Outputs (gitignored under `out/`):

| Path | Purpose |
|------|---------|
| `out/findings.json` | Structured scan findings |
| `out/notion/explainer.md` | ExplainDiff-style explainer + 5-question quiz |
| `out/notion/decisions.csv` | Notion Decisions DB import template |
| `out/notion/decisions.json` | Same schema as JSON |

**Microworld:** open `hitl/microworld/index.html` locally (see `hitl/microworld/README.md`) to scrub through agent reasoning steps.

**Notion spec:** `hitl/NOTION-HITL.md` documents the Decisions database properties and multiplayer workflow.

### Geoffrey Litt — Explanations / Micro worlds / Shared spaces

This HITL loop implements ideas from [Geoffrey Litt's talk on explorable explanations](https://www.youtube.com/watch?v=WkBPX-oDMnA):

| Pillar | In this repo | Artifact |
|--------|--------------|----------|
| **Explanations** | Literate walkthrough + quiz gate | `out/notion/explainer.md` |
| **Micro worlds** | Local scrubber playground | `hitl/microworld/index.html` |
| **Shared spaces** | Multiplayer Notion Decisions DB | `hitl/NOTION-HITL.md`, `out/notion/decisions.csv` |

**Gate:** A run is Approved only if the reviewer passes the quiz or records an explicit waiver in Notion.

## Production reviewer (real scan findings)

After a live or dry-run scan, the pipeline writes **`output/{slug}-{YYYY-MM}.findings.json`** next to the HTML report. Reviewer decisions **autosave to disk** on every lock — browser localStorage is a cache only, not the source of truth.

```bash
docker compose up --build
# Submit a scan at http://127.0.0.1:8080 — when finished, click "Review findings"

# Or demo without a full scan:
make review-demo
open http://127.0.0.1:8080/review/becaps
```

| Route | Purpose |
|-------|---------|
| `GET /review/<job_id>` | Production reviewer UI (EN/ES) |
| `GET /api/review/<job_id>/findings` | Load findings JSON for a job |
| `POST /api/review/<job_id>/locks` | Autosave locks (debounced after each lock) |
| `POST /api/review/<job_id>/locks/merge` | Recover: merge server + localStorage on load |

**Server SoT path:** `output/{job_id}-review-locks.json` (e.g. `output/becaps-review-locks.json`).

**Durability:** UI shows green “Saved to disk: path” or red “Unsaved — only in this browser”. Download JSON is always available (empty skeleton when zero locks).

**Finding IDs:** `S001…` from score-derived gaps/docs/eligibility; `F001…` from fixture microworld (`make hitl-demo`).

**Mapping (score → findings):**

| Source | Rule | Label (default) |
|--------|------|-----------------|
| Pillar `gaps` | `score_gap` | `needs_human` if status needs_work/partial; `unclear` if developing/emerging |
| Pillar `missing_docs` | `missing_doc` | Same as pillar status |
| Pillar `docs_weak` | `weak_doc` | Same as pillar status |
| Eligibility `fail` | `eligibility_fail` | `needs_human` |
| Eligibility `warn` | `eligibility_warn` | `unclear` |
| Strong pillar, no gaps | `pillar_strong` | `auto_ok` |

Locks export as **`review-locks.json`** (microworld locks schema v1 fields; `fixture_path` holds `source_path`).

**Notion (optional team SoT):** after Playground review, push via Infisical env token only:
`python scripts/push_microworld_to_notion.py --locks output/becaps-review-locks.json`
The Shared Decisions database remains the multiplayer audit surface once Gideon chooses to promote from Playground.

**Training microworld** (VertiGreen fixtures, quiz gate) stays at `hitl/microworld/index.html` — see `hitl/microworld/README.md`.

### Understanding Lab Playground (direction)

The Playground must become **durable**, not browser-only: scenario → consequences → options → choose should persist the same way as production reviewer locks (server autosave + recovery merge). This PR establishes that pattern for scan findings; the Playground slice will reuse it.

Auth: localhost-only in v1 (same as scan form). Upload may already have run; v1 treats locked decisions as audit trail.

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
- `output/{slug}-{YYYY-MM}.findings.json` — reviewable findings (S-prefixed)
- `output/{job_id}-review-locks.json` — autosaved reviewer locks (server SoT)

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
┌──────────┐     ┌───────┐     ┌────────┐
│  Web UI  │────▶│ Redis │────▶│ Worker │
│ :8080    │     │  RQ   │     │        │
└──────────┘     └───────┘     └───┬────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              Drive API      Anthropic API   Playwright
              (crawl/upload)  (scoring)      (PDF)
```

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
| `app/main.py` + RQ worker | ✅ HTTP form + queue |
| `compose.yml` | ✅ Redis + web + worker + Playwright |
| `scripts/dry_run.py` + `tests/` | ✅ Dry-run + pytest |
| Production reviewer UI (`/review`) | ✅ Score findings + server autosave locks |
| Caddy TLS edge | [PENDIENTE] |
| CI pipeline | [PENDIENTE] |
| VPS deploy (Hands) | [PENDIENTE] |
