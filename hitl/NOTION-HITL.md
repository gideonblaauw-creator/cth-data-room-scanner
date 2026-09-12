# Notion HITL — Shared Space Spec

This document defines the **Shared space** for Dataroom Reviewer human-in-the-loop workflows, inspired by Geoffrey Litt's *Explanations / Micro worlds / Shared spaces* framing ([talk](https://www.youtube.com/watch?v=WkBPX-oDMnA)).

## Purpose

The Decisions database is the multiplayer surface where:

1. The **agent** creates rows after each fixture scan (`make hitl-demo`)
2. The **human reviewer** sets `Human decision`, `Rationale`, and `Quiz passed`
3. The **run** is gated: **Approved** only if quiz passed or explicitly waived

No live Notion write is required for v1 — import `out/notion/decisions.csv` or use the JSON template.

## Database: Decisions

| Property | Type | Set by | Description |
|----------|------|--------|-------------|
| **Finding ID** | Title | Agent | Stable ID from `findings.json` (e.g. `F004`) |
| **Fixture path** | Text | Agent | Relative path under `fixtures/sample-dataroom/` |
| **Agent suggestion** | Text | Agent | `{label} → {action}` (e.g. `needs_human → confirm_redaction`) |
| **Human decision** | Select | Human | `agree` \| `override` \| `defer` |
| **Rationale** | Text | Human | Why the human agreed or overrode the agent |
| **Quiz passed** | Checkbox | Human | True when reviewer completed explainer quiz |
| **Status** | Select | Human | `pending` \| `reviewed` \| `waived` \| `blocked` |
| **Run link** | URL | Agent | Link to `out/findings.json` or CI artifact |
| **Reviewer** | Person | Human | Gideon / assigned reviewer |

### Select options

**Human decision**

- `agree` — accept agent label and action
- `override` — different label or action (document in Rationale)
- `defer` — needs more context or external counsel

**Status**

- `pending` — default on import
- `reviewed` — human decision recorded
- `waived` — quiz or review explicitly waived (audit trail in Rationale)
- `blocked` — cannot proceed (e.g. missing fixture)

## 5-beat lab flow (timeboxed)

Full HITL gate target: **≤ 10 minutes** end-to-end. The microworld alone is **~2–3 minutes**.

| Beat | Pillar | Artifact | Timebox |
|------|--------|----------|---------|
| 1 | Scan | `make hitl-demo` → `out/findings.json` | ~1 min |
| 2 | Explanations | `out/notion/explainer.md` (background + intuition) | ~3 min |
| 3 | **Micro worlds** | `hitl/microworld/index.html` — VertiGreen decision moments | **~2–3 min** |
| 4 | Shared spaces | Notion **Decisions DB** — agree / override / defer + rationale | ~3 min |
| 5 | Gate | Quiz passed or waived → **Approved** | ~1 min |

**Placement:** Beat 3 (microworld) sits **between Explainer and Decisions** — reviewers practice four synthetic VertiGreen calls (IBAN redaction, unaudited financials, ambiguous SAFE/cap table, hallucinated metric reject) before recording decisions in Notion.

**Major-PR-only gate:** The full 5-beat gate (quiz + Decisions DB sign-off) applies to **major PRs** that change scanner rules, fixture expectations, or HITL workflow artifacts. Routine doc-only or minor fixes may skip the Notion gate; record any skip in PR description.

## Workflow

```mermaid
flowchart LR
  A[make hitl-demo] --> B[out/findings.json]
  A --> C[out/notion/explainer.md]
  A --> D[out/notion/decisions.csv]
  C --> E[Beat 2: Explainer]
  E --> F[Beat 3: Microworld]
  F --> G[Beat 4: Decisions DB]
  B --> G
  D --> G
  G --> H{Beat 5: Quiz passed or waived?}
  H -->|yes| I[Run Approved]
  H -->|no| J[Run Blocked]
```

## Multiplayer rules

| Actor | Creates | Updates |
|-------|---------|---------|
| Agent (CI / Hands) | Rows, Run link, Agent suggestion | Re-run replaces stale rows (new Run link) |
| Human (Gideon) | — | Human decision, Rationale, Quiz passed, Status, Reviewer |

## Importing decisions.csv

1. Run `make hitl-demo` locally or download CI artifacts
2. In Notion: New database → Import → CSV → `out/notion/decisions.csv`
3. Map columns to properties above (types may need adjustment after import)
4. Open `out/notion/explainer.md` in Notion or the repo; complete the quiz
5. Check **Quiz passed** on each row (or one parent Run page) before marking Approved

## Safety

- **Synthetic fixtures only** — `fixtures/sample-dataroom/` contains fictional VertiGreen data
- No Infisical, Monday, or client tokens in this workflow
- Do not point HITL demo at production Drive folders

## Related artifacts

| Artifact | Litt pillar | Path |
|----------|-------------|------|
| Explainer + quiz | Explanations | `out/notion/explainer.md` |
| VertiGreen microworld (EN/ES, 4 moments) | Micro worlds | `hitl/microworld/index.html` |
| Decisions DB | Shared spaces | `out/notion/decisions.csv` |

## Gate note

> **Approved** only if quiz passed or waived. Record waivers in **Rationale** for audit.
