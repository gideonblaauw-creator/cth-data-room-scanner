# CTH Data Room Scanner

Scans a startup's Google Drive data room and produces a branded due diligence report
(HTML + PDF) aligned to CTH's 8-pillar Growth Services framework.

## Who uses this

CTH team — Gideon, Jop, Brian (Kwakman).
Requires: Claude Code (CTH Desktop 1) + Google Drive MCP connected in Claude Desktop.

## Before your first scan

1. Clone this repo and run `pip install playwright --break-system-packages && playwright install chromium`
2. Copy `.env.example` → `.env` and add your `DRIVE_REPORTS_FOLDER_ID` (ask Gideon)
3. Confirm Google Drive is connected in Claude Desktop → Settings → Connectors

## How to run a scan

Open Claude Code and type:

```
/scan https://drive.google.com/drive/folders/FOLDER_ID
```

Claude will ask for:
- Company name (if not in the URL)
- Language (default: Spanish)
- Any context not visible in the Drive (round size, stage, founder notes)

Then it crawls, scores, renders, and uploads automatically.

## Outputs

Local copies (gitignored):
- `output/{slug}-{YYYY-MM}.html` — open in browser to review
- `output/{slug}-{YYYY-MM}.pdf`  — ready to send

In shared Drive (everyone sees immediately):
- `CTH Growth Services / Reports / {YYYY-MM} / {slug} /`
  - `{slug}-{YYYY-MM}.html`
  - `{slug}-{YYYY-MM}.pdf`

## After the scan

1. Open the HTML report in your browser — review scores, check findings
2. If edits needed: edit `output/{slug}.html` directly, then re-upload:
   - In Claude Code: "re-upload output/{slug}.html and output/{slug}.pdf to Drive"
3. Download the PDF from Drive and attach to the founder email (send manually)
4. Schedule the 30-min follow-up call

Optional — public URL (Gideon only):
```
scp output/{slug}-{YYYY-MM}.html root@51.195.45.77:/var/www/reportes/
```
→ `https://reportes.cleantechhub.net/{slug}-{YYYY-MM}.html`

## Calibration reference

BeCaps (April 2026): 3.5/5 — GO Phase 1. Use as scoring benchmark.
Drive folder ID: `1sg4TlFoP2_YVYmDdxuacC3Gs4kpB0Bd_`

## Adding a new team member

1. Add them to the GitHub repo (write access)
2. Share the "CTH Growth Services / Reports" Drive folder with them (Editor)
3. They clone, install deps, copy .env.example → .env, add folder ID
4. No VPS access needed — ever

## Current team

- Gideon Blaauw — gideon.blaauw@cleantechhub.net
- Jop Blom — jop.blom@cleantechhub.net
- Brian Kwakman — brian.kwakman@behold.nl
