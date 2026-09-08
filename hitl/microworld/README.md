# Microworld — Finding Scrubber Playground

A **local, self-contained** learning artifact for stepping through synthetic agent reasoning on dataroom findings. This is not production UI.

## How to open

1. Run the HITL demo to generate findings:
   ```bash
   make hitl-demo
   ```
2. Open the microworld in a browser:
   ```bash
   # macOS
   open hitl/microworld/index.html

   # Linux
   xdg-open hitl/microworld/index.html

   # Or serve locally (optional)
   python -m http.server 8765 --directory hitl/microworld
   # then visit http://127.0.0.1:8765/
   ```
3. Click **Load findings.json** and select `out/findings.json` from the repo root (file picker cannot read arbitrary paths without user action).

## What it shows

For each finding:

- **File** — fixture path in `fixtures/sample-dataroom/`
- **Rule fired** — deterministic rule ID (e.g. `R002`)
- **Suggested action** — agent proposal (`confirm_redaction`, `legal_review`, etc.)
- **Scrubber** — step through reasoning steps one at a time

## Offline fallback

If no `findings.json` is loaded, the page uses embedded sample data from the VertiGreen fixture so you can explore the UI without running the demo first.

## Geoffrey Litt mapping

This microworld is the **Micro worlds** pillar — a small explorable environment to build intuition before making decisions in the shared Notion space.
