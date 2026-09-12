# Review static demo (NOT production)

**Demo only — not production review.**

Lightweight HTML shell that loads baked BeCaps-style findings from `findings-becaps-demo.json`. Derived from public CTH calibration metadata (`fixtures/becaps_scoring.json` / skills doc). No Flask, no Drive API, no Notion tokens.

## Serve locally

```bash
python3 -m http.server 8766 --directory hitl/review-static
# → http://127.0.0.1:8766/
```

## Do not

- Deploy this folder to public Vercel with real client findings
- Treat this as the production `/review` UI (that stays localhost / Tailscale)

## Public training microworld

For the synthetic VertiGreen HITL lab (safe for public Vercel), see `hitl/STABLE-HOST.md` and https://cth-hitl-lab.vercel.app/
