# Scanner Understanding Lab — LexiScan House Tour

LexiScan-standard **HTML house tour** for the Dataroom Reviewer HITL loop (CleantechHUB Scanner product). Implements Infra format lock **t1268u** — shared LexiScan house-tour layout (floor plan + corridor rooms, not tabs). Replaces the legacy tabbed shell at `hitl/microworld/`.

## Shared decisions (Notion)

Locked decisions export to the CleantechHUB **Shared decisions** database:

**https://app.notion.com/p/bb52cfa45b6744e59983528480fbab4b**

After lock-in, download ledger JSON from the sidebar and push via `scripts/push_microworld_to_notion.py` (token in env only — never in the browser).

## Serve locally

```bash
# From repo root (so fixture paths resolve)
python3 -m http.server 8765

# Visit
open http://127.0.0.1:8765/understanding-lab/playground/
```

## House layout

| Room | Legacy tab | Purpose |
|------|------------|---------|
| **Foyer** | — | Welcome + tour start |
| **Context Room** | Context | Why HITL, VertiGreen sample, 5-beat flow |
| **Explainer Hall** | Explainer | Agent labels, human decisions, 5-question quiz (gates corridor) |
| **Decision Corridor** | Decision Tree hub | Floor-plan hub to finding doors |
| **Decision doors** | Decision Tree | Per-finding scrubber + agree/override/defer lock-in |
| **Ledger sidebar** | Decisions DB | Local locks + JSON/MD export (LexiScan ledger shape) |
| **Repo Archive** | GH repo | Repo links, path map, fixture→finding map |
| **Clarifications Nook** | Clarifications | Deferral notes (localStorage + export) |

Navigation uses a **floor plan** with corridor connectors (not tabs). EN/ES via `nameEn` / `nameEs` in `data.js`.

## One-command local loop

```bash
make hitl-demo
python3 -m http.server 8765
# Complete Explainer quiz → lock each finding door → download ledger JSON
python scripts/push_microworld_to_notion.py --dry-run
python scripts/push_microworld_to_notion.py
```

## Files

| File | Role |
|------|------|
| `index.html` | Shell + welcome overlay |
| `data.js` | Rooms, quiz, i18n (`nameEn`/`nameEs`) |
| `app.js` | House tour logic, ledger, persistence |
| `styles.css` | CTH lime chrome, floor-plan layout |
| `smoke.sh` | Static checks (no browser) |
| `defaults/` | Bundled findings fixture |

## Persistence (localStorage)

Uses `cth_scanner_playground_*` keys and **reads legacy** `cth_microworld_*` keys for backward compatibility.

## Canonical format (t1268u)

Infra owns LexiScan house-tour format (t1268u); FabFloow owns LexiScan product. Canonical reference:

https://github.com/gideonblaauw-creator/fabfloow-lexiscan/tree/main/understanding-lab/playground

JSON export includes `schema_version`, `playground_id: "cth-scanner-ul-playground-v1"`, and Scanner lock fields. Markdown export includes a `## Decision table` pipe summary before per-lock sections.
