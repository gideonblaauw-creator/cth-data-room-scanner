# Microworld — Interactive Decision Lock-in

A **local, self-contained** HITL microworld where the human reviewer consciously locks each decision before it reaches the Notion Decisions database. Synthetic VertiGreen fixtures only — not production UI.

## One-command local loop

```bash
# 1. Generate findings + explainer quiz outputs
make hitl-demo

# 2. (Optional) Save quiz answers after completing out/notion/explainer.md quiz
cp hitl/microworld/quiz-answers.example.json hitl/out/quiz-answers.json

# 3. Open microworld — serve from repo root so quiz/findings paths resolve
python -m http.server 8765
# Visit http://127.0.0.1:8765/hitl/microworld/

# 4. Click through gate findings, lock each with rationale (no bulk approve)

# 5. Download microworld-locks.json → save to hitl/out/microworld-locks.json

# 6. Push to Notion Decisions DB
python hitl/scripts/push_microworld_to_notion.py --dry-run   # validate first
python hitl/scripts/push_microworld_to_notion.py             # requires NOTION_API_TOKEN
```

**No token?** Use `--paste-pack` for manual Notion entry, or copy the in-app paste pack from the end screen.

## Dataflow

```
Explainer quiz                Microworld (this page)           Decisions DB
─────────────────            ───────────────────────          ─────────────
out/notion/explainer.md  →   hitl/out/quiz-answers.json  →   (quiz_passed flag)
        │                              │
        │                              ▼
out/findings.json        →   lock decisions + rationale  →   hitl/out/microworld-locks.json
        │                              │
defaults/findings-       →   (banner if quiz missing)         push_microworld_to_notion.py
hitl-20260908-214515.json                                      → Notion Decisions DB
```

## Initialization sources

| Input | Path / param | Fallback |
|-------|----------------|----------|
| Quiz answers | `hitl/out/quiz-answers.json`, `?quiz=…` | Demo defaults + banner |
| Findings | `out/findings.json`, `?findings=…` | `defaults/findings-hitl-20260908-214515.json` |

## UX states

Each gate finding moves: **unlocked** → **decided** (draft) → **locked** (immutable).

- Lock requires explicit confirm + rationale (min 8 chars)
- Unlock requires confirm — no silent edits
- No bulk-approve — one conscious decision at a time
- EN / ES toggle preserved
- ~7 gate moments (~2–3 min): IBAN redaction, unaudited financials, SAFE/cap table, hallucinated metric, etc.

## Environment variables (push script only — never in browser)

| Variable | Purpose |
|----------|---------|
| `NOTION_API_TOKEN` | Notion integration token (or `NOTION_TOKEN`) |
| `NOTION_DECISIONS_DATA_SOURCE_ID` | CleantechHUB collection (`5f2cca6c-867a-4884-a365-0f693c0dbf27`) |

## Gate reminder

> **Approved** only if quiz passed or explicitly waived. Record waivers in **Rationale** for audit. Major PR gate: Explainer + Decisions + microworld locks ≤ 10 findings.

## Related

- Shared space spec: `hitl/NOTION-HITL.md`
- Decisions DB: https://app.notion.com/p/bb52cfa45b6744e59983528480fbab4b
