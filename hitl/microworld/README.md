# Microworld — Tabbed HITL Review Loop

A **local, self-contained** tabbed HTML app for the Dataroom Reviewer HITL loop. Merges the Explainer quiz, interactive decision lock-in microworld, Decisions DB mirror, GH repo map, and clarifications capture. Synthetic VertiGreen fixtures only — not production UI.

## Serve locally

```bash
# From repo root (so fixture/quiz paths resolve)
python3 -m http.server 8765

# Visit
open http://127.0.0.1:8765/hitl/microworld/
```

## Tabs

| Tab | Purpose |
|-----|---------|
| **Context** | Why HITL, VertiGreen sample, 5-beat flow, why browser cannot auto-push Notion |
| **Explainer** | Agent labels, agree/override/defer, 5-question quiz (gates Decision Tree) |
| **Decision Tree** | Interactive lock-in per finding moment (F001–F010 style) |
| **Decisions DB** | Local locks mirror + link to live Notion DB |
| **GH repo** | Repo links, path map, fixture→finding map |
| **Clarifications** | Deferral / needs-clarification notes (localStorage + export) |

## One-command local loop

```bash
# 1. Generate findings + explainer outputs
make hitl-demo

# 2. Open microworld (see serve command above)

# 3. Complete Explainer quiz → lock each gate finding in Decision Tree

# 4. Download microworld-locks.json → save to hitl/out/microworld-locks.json

# 5. Push to Notion Decisions DB (token from env only — never in browser)
python scripts/push_microworld_to_notion.py --dry-run
python scripts/push_microworld_to_notion.py
```

**No token?** Use `--paste-pack` for manual Notion entry, or copy JSON from the "Locks ready" banner.

## Why auto-push failed (by design)

The browser **must not hold Notion secrets**. Tokens live in Infisical / environment only. After lock-in:

1. Browser stores decisions in **localStorage** and offers **Download** / **Copy JSON**
2. Infra or Hands push via `scripts/push_microworld_to_notion.py` with `NOTION_API_TOKEN`
3. Or paste manually into the [Decisions DB](https://app.notion.com/p/bb52cfa45b6744e59983528480fbab4b)

## Locks JSON schema

```json
{
  "version": 1,
  "run_id": "hitl-20260908-214515",
  "company": "VertiGreen Robotics",
  "quiz_passed": true,
  "quiz_source": "explainer-quiz",
  "locked_at": "2026-09-12T14:00:00+00:00",
  "reviewer": null,
  "run_link": "hitl/out/microworld-locks.json",
  "locks": [{
    "finding_id": "F004",
    "fixture_path": "financials-summary.md",
    "agent_suggestion": "manual_review",
    "agent_label": "needs_human",
    "human_decision": "agree",
    "rationale": "Draft financials flagged correctly.",
    "status": "reviewed",
    "locked_at": "2026-09-12T14:00:01+00:00",
    "moment": "unaudited_financials"
  }]
}
```

Gideon's completed run (`hitl-20260908-214515`) locked F001, F004, F005, F006, F008, F009, F010 — schema is backward-compatible.

## Environment variables (push script only)

| Variable | Purpose |
|----------|---------|
| `NOTION_API_TOKEN` | Notion integration token (or `NOTION_TOKEN`) |
| `NOTION_DECISIONS_DATA_SOURCE_ID` | CleantechHUB collection (optional; has default) |

## Initialization sources

| Input | Path / param | Fallback |
|-------|----------------|----------|
| Findings | `out/findings.json`, `?findings=…` | `defaults/findings-hitl-20260908-214515.json` |
| Quiz | In-app Explainer tab | localStorage `cth_microworld_quiz` |
| Decisions | Decision Tree tab | localStorage `cth_microworld_decisions` |
| Clarifications | Clarifications tab | localStorage `cth_microworld_clarifications` |

## Related

- Shared space spec: `hitl/NOTION-HITL.md`
- Decisions DB: https://app.notion.com/p/bb52cfa45b6744e59983528480fbab4b
- Explainer (Notion): https://app.notion.com/p/3d5dfee50be9816db4dec71e885a1f7d
