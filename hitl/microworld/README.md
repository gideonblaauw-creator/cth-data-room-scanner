# Microworld — Moved to Understanding Lab

> **Legacy path.** The tabbed shell (`Context / Explainer / Decision Tree / …`) is **not** the LexiScan standard format.

## New location

**`understanding-lab/playground/`** — LexiScan HTML house tour (floor plan + corridor rooms).

```bash
python3 -m http.server 8765
open http://127.0.0.1:8765/understanding-lab/playground/
```

This directory keeps a thin redirect in `index.html` so old links do not silently die. Product content, quiz, decision lock-in, ledger export, and EN/ES are preserved in the new playground.

See [`understanding-lab/playground/README.md`](../../understanding-lab/playground/README.md) for the full loop.

## What stayed here

| Path | Purpose |
|------|---------|
| `defaults/` | Findings fixture (also copied to playground) |
| `schema/` | `microworld-locks.schema.json` |
| `quiz-answers.example.json` | Example quiz export |

Push script and Notion integration unchanged: `scripts/push_microworld_to_notion.py`.
