# /scan — CTH Data Room Scanner

Scan a startup's Google Drive data room and produce a due diligence report.

## Usage

```
/scan <google-drive-folder-url-or-id> [--lang es|en] [--client "Company Name"]
```

## What I will do

1. Extract the folder ID from the URL
2. Crawl the entire Drive folder recursively using the Google Drive MCP
3. Read all key documents (PDFs, Docs, Sheets, Slides, text files)
4. Score the company across 8 pillars using the CTH Growth Services framework
5. Render the branded HTML report from the template
6. Convert HTML to PDF using Playwright
7. Save both files to output/ locally
8. Upload both files to the shared CTH Google Drive reports folder
9. Print the Drive folder URL where the team can access the report

## Before starting, ask me for

- Company name (if not provided via --client flag)
- Language preference (default: Spanish / es)
- Any context not visible in the Drive (round size, stage, founder notes)

## Reports Drive folder

```
DRIVE_REPORTS_FOLDER_ID=1RvuoSvbm6SvbdCWU06Wa7jyfEniPmzbP
URL: https://drive.google.com/drive/folders/1RvuoSvbm6SvbdCWU06Wa7jyfEniPmzbP
```

Upload structure: `Reports / {YYYY-MM} / {company-slug} / {slug}-{YYYY-MM}.html + .pdf`

## Step-by-step execution

### Step 1 — Parse input

Extract the Google Drive folder ID from the argument. Accept both:
- Full URL: `https://drive.google.com/drive/folders/FOLDER_ID`
- Raw ID: `1sg4TlFoP2_YVYmDdxuacC3Gs4kpB0Bd_`

Parse optional flags:
- `--lang es` or `--lang en` (default: `es`)
- `--client "Company Name"` (if not provided, ask)

### Step 2 — Crawl the Drive folder

Use the Google Drive MCP tools to recursively list all files and folders:

1. Call `search_files` or `list_recent_files` with the folder ID to get all children
2. For each subfolder, recurse
3. Build a tree structure matching the schema in `scanner/crawl.py`

Prioritize reading files whose names match `PRIORITY_FILE_KEYWORDS` from `scanner/crawl.py`:
- one-pager, pitch, deck, CV, cap table, financial projections, impact docs, pipeline

Read up to 20 files fully (first 4000 chars each). For other files, note their names and types.

### Step 3 — Score across 8 pillars

Read `skills/cth-growth-services.md` for the full framework, scoring criteria, and calibration reference.

For each of the 8 pillars, produce:
- **Score** (1.0–5.0, one decimal)
- **Status** (strong / emerging / developing / partial / needs_work)
- **Summary** (1-2 sentences)
- **Strengths** (bullet list)
- **Gaps** (bullet list)
- **Missing docs** (what should be in the data room but isn't)
- **CTH Phase 1 actions** (what CTH would do first)
- **Docs present / weak / missing** (tagged lists)

The 8 pillars are:
1. **bm** — Business Model
2. **team** — Team & Founders
3. **traction** — Traction & Clients
4. **financials** — Financial Model & Projections
5. **impact** — Climate / ESG Impact
6. **legal** — Legal, IP & Corporate Structure
7. **market** — Market & Competition
8. **investor_readiness** — Investor Readiness & Materials

Also produce:
- **Overall score** (average of 8 pillars)
- **Recommendation** (go_phase1 / tier2 / not_ready / decline)
- **Verdict** (title + body)
- **Eligibility checks** (stage, round_size, climate_fit, exclusivity, co_creation)
- **Key metrics** (5 cards)
- **Action plans** (Phase 1 and Phase 2)

Output the full JSON structure matching `SCORING_OUTPUT_SCHEMA` in `scanner/score.py`.

### Step 4 — Render HTML report

Run the renderer:

```python
import sys
sys.path.insert(0, '/opt/cth-data-room-scanner')
from scanner.render import render_report, save_html
from scanner.render import slugify

slug = slugify(company_name)
scan_date = "YYYY-MM-DD"  # today

html = render_report(scoring_json, lang=lang)
html_path = save_html(html, slug, scan_date)
```

### Step 5 — Generate PDF

```python
from scanner.pdf import convert

pdf_path = html_path.replace('.html', '.pdf')
success = convert(html_path, pdf_path)
```

If Playwright fails and WeasyPrint also fails, save the HTML only and note the PDF failure.

### Step 6 — Upload to shared Drive

Use the Google Drive MCP to upload both files to the shared reports folder:

1. Check/create month subfolder: `Reports / {YYYY-MM} /`
2. Check/create company subfolder: `Reports / {YYYY-MM} / {slug} /`
3. Upload `{slug}-{YYYY-MM}.html` (mimeType: text/html)
4. Upload `{slug}-{YYYY-MM}.pdf` (mimeType: application/pdf)
5. Print the Drive folder URL

### Step 7 — Summary

Print a summary:
```
✅ Scan complete: {company_name}
   Score: {overall_score}/5.0 — {recommendation}
   HTML:  output/{slug}-{YYYY-MM}.html
   PDF:   output/{slug}-{YYYY-MM}.pdf
   Drive: https://drive.google.com/drive/folders/{company_folder_id}
```

## Framework reference

Read `skills/cth-growth-services.md` before scoring. This contains:
- The 8-pillar framework and scoring criteria
- CTH eligibility filter thresholds
- Phase 1 and Phase 2 action plan templates
- BeCaps test case as calibration reference (score: 3.5/5)

## Calibration

BeCaps (April 2026): overall 3.5/5 — GO Phase 1.
Use as scoring benchmark. If your scoring diverges significantly from this reference, recalibrate.

## Output files

- `output/{slug}-{YYYY-MM}.html` — interactive report
- `output/{slug}-{YYYY-MM}.pdf` — PDF version
- Drive: `CTH Growth Services / Reports / {YYYY-MM} / {slug} /`
