# Notion HITL — Shared Space Spec

This document defines the **Shared space** for Dataroom Reviewer human-in-the-loop workflows, inspired by Geoffrey Litt's *Explanations / Micro worlds / Shared spaces* framing ([talk](https://www.youtube.com/watch?v=WkBPX-oDMnA)).

## Purpose

The Decisions database is the multiplayer surface where:

1. The **agent** creates rows after each fixture scan (`make hitl-demo`)
2. The **human reviewer** locks decisions in the **microworld** with explicit rationale
3. Locked decisions are pushed to Notion via `hitl/scripts/push_microworld_to_notion.py`
4. The **run** is gated: **Approved** only if quiz passed or explicitly waived

**Security:** Notion API tokens never go in browser HTML. The microworld writes `hitl/out/microworld-locks.json`; the push script uses env/Infisical credentials.

## Database: Decisions

**Notion page:** https://app.notion.com/p/bb52cfa45b6744e59983528480fbab4b  
**Data source:** `collection://5f2cca6c-867a-4884-a365-0f693c0dbf27` (CleantechHUB)

| Property | Type | Set by | Description |
|----------|------|--------|-------------|
| **Finding ID** | Title | Agent / Microworld | Stable ID from `findings.json` (e.g. `F004`) |
| **Fixture path** | Text | Agent | Relative path under `fixtures/sample-dataroom/` |
| **Agent suggestion** | Text | Agent | `{label} → {action}` (e.g. `needs_human → confirm_redaction`) |
| **Human decision** | Select | Human | `agree` \| `override` \| `defer` |
| **Rationale** | Text | Human | Why the human agreed or overrode the agent |
| **Quiz passed** | Checkbox | Human | True when reviewer completed explainer quiz |
| **Status** | Select | Human | `pending` → `reviewed` (on lock) |
| **Run link** | URL | Agent | Link to run artifact or `hitl/out/microworld-locks.json` |
| **Reviewer** | Person | Human | Gideon / assigned reviewer (optional) |

### Select options

**Human decision**

- `agree` — accept agent label and action
- `override` — different label or action (document in Rationale)
- `defer` — needs more context or external counsel

**Status**

- `pending` — default before lock
- `reviewed` — human decision locked in microworld
- `waived` — quiz or review explicitly waived (audit trail in Rationale)
- `blocked` — cannot proceed (e.g. missing fixture)

## Dataflow: Quiz → Microworld → Decisions DB

```
┌─────────────────────┐     ┌──────────────────────────┐     ┌─────────────────────┐
│  EXPLAINER (quiz)   │     │  MICROWORLD (browser)    │     │  DECISIONS DB       │
│  out/notion/        │     │  hitl/microworld/        │     │  Notion Cleantech   │
│  explainer.md       │     │  index.html              │     │  HUB collection     │
└─────────┬───────────┘     └────────────┬─────────────┘     └──────────┬──────────┘
          │                              │                               │
          │  complete 5-question quiz    │  click + lock each finding    │
          ▼                              ▼                               ▼
   hitl/out/quiz-answers.json    hitl/out/microworld-locks.json    push_microworld_to_notion.py
          │                              │                               │
          └──────── initializes ─────────┘                               │
                     microworld                                          │
                                                                         ▼
                                                              rows in Decisions DB
```

### One-command local loop

```bash
make hitl-demo
python -m http.server 8765
# open http://127.0.0.1:8765/hitl/microworld/
# lock all gate findings → download → save as hitl/out/microworld-locks.json
python hitl/scripts/push_microworld_to_notion.py --dry-run
python hitl/scripts/push_microworld_to_notion.py
```

**Offline fallback:** `python hitl/scripts/push_microworld_to_notion.py --paste-pack` or import `out/notion/decisions.csv`.

## Multiplayer rules

| Actor | Creates | Updates |
|-------|---------|---------|
| Agent (CI / Hands) | Rows, Run link, Agent suggestion | Re-run replaces stale rows (new Run link) |
| Human (Gideon) | — | Locks in microworld → push sets Human decision, Rationale, Quiz passed, Status |

Microworld enforces **conscious lock-in**: each decision needs confirm + rationale; no bulk-approve.

## Environment variables (push script)

| Variable | Required | Description |
|----------|----------|-------------|
| `NOTION_API_TOKEN` | Yes (live push) | Notion integration token |
| `NOTION_DECISIONS_DATA_SOURCE_ID` | No | Defaults to CleantechHUB `5f2cca6c-867a-4884-a365-0f693c0dbf27` |

Load from Infisical or `.env` locally — **never** embed in `index.html`.

## Importing decisions.csv (legacy / bulk seed)

1. Run `make hitl-demo` locally or download CI artifacts
2. In Notion: Import → CSV → `out/notion/decisions.csv`
3. Complete explainer quiz; save `hitl/out/quiz-answers.json`
4. Use microworld to lock decisions; push or paste-pack

## Safety

- **Synthetic fixtures only** — `fixtures/sample-dataroom/` contains fictional VertiGreen data
- No Infisical, Monday, or client tokens in browser workflows
- Do not point HITL demo at production Drive folders

## Related artifacts

| Artifact | Litt pillar | Path |
|----------|-------------|------|
| Explainer + quiz | Explanations | `out/notion/explainer.md` |
| Quiz handoff | Explanations → Microworld | `hitl/out/quiz-answers.json` |
| Interactive lock-in | Micro worlds | `hitl/microworld/index.html` |
| Lock output | Micro worlds → Shared space | `hitl/out/microworld-locks.json` |
| Notion push | Shared spaces | `hitl/scripts/push_microworld_to_notion.py` |
| Decisions DB seed | Shared spaces | `out/notion/decisions.csv` |

## Gate note

> **Approved** only if quiz passed or waived. Record waivers in **Rationale** for audit.  
> Major PR gate: Explainer + Decisions + microworld gate findings ≤ 10.
