# Microworld — VertiGreen HITL Micro-Sim

A **local, self-contained** guided review (~2–3 min) for practicing human-in-the-loop decisions on synthetic VertiGreen dataroom findings. This is not production UI.

## How to open

Open directly in a browser — no server or `findings.json` required:

```bash
# macOS
open hitl/microworld/index.html

# Linux
xdg-open hitl/microworld/index.html

# Or serve locally (optional)
python -m http.server 8765 --directory hitl/microworld
# then visit http://127.0.0.1:8765/
```

Link from Notion: paste the file path or host the static HTML on any static host.

## What it covers (4 moments)

| # | Scenario | Finding | Decision |
|---|----------|---------|----------|
| 1 | IBAN partial redaction | F005 | `confirm_redaction` |
| 2 | Unaudited financial projections | F004 | `verify_financials` |
| 3 | Ambiguous SAFE / cap table | F006 | `verify_cap_table` |
| 4 | Hallucinated impact metric (42% vs 34.8%) | F-HALL | `reject_hallucination` |

Each moment: read agent suggestion → choose **agree**, **override**, or **defer** → brief feedback.

## EN / ES

Toggle **EN** / **ES** in the header. All copy swaps via client-side strings.

## End screen

**Return to Decisions DB** links to the Notion placeholder:

`https://app.notion.com/p/bb52cfa45b6744e59983528480fbab4b`

## Lab placement

Beat 3 in the 5-beat HITL flow — **after** `out/notion/explainer.md`, **before** the Notion Decisions database. See `hitl/NOTION-HITL.md`.

## Geoffrey Litt mapping

This microworld is the **Micro worlds** pillar — a small explorable environment to build intuition before making decisions in the shared Notion space.
