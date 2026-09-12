# HITL stable static host

Permanent public URLs for **training-only** HITL HTML. No Notion tokens, no live client Drive data.

## Product split

| Surface | Data | Host |
|---------|------|------|
| **Microworld** (`hitl/microworld/`) | Synthetic VertiGreen fixtures | Public Vercel (this doc) |
| **Production review** (`/review` with real findings) | Client dataroom scans | localhost / Tailscale only — **never** on public Vercel |

## Stable URL — microworld (training)

**Production:** https://cth-hitl-lab.vercel.app/

- Vercel project: `cth-hitl-lab`
- Root directory: `hitl/microworld`
- Deployment protection: **off** (public, no SSO)
- Default findings: `defaults/findings-hitl-20260908-214515.json` (bundled, relative path)

Print from repo:

```bash
make hitl-host-url
```

## Local static serve (no Flask)

```bash
make hitl-static-serve
# → http://127.0.0.1:8765/
```

Uses `hitl/microworld` as document root so `defaults/*.json` resolve correctly.

## Deploy / update (Infra)

### Option A — Git-linked (preferred after merge)

```bash
# From repo root; requires Vercel CLI login or MCP
vercel link --project cth-hitl-lab --cwd hitl/microworld
vercel --prod --cwd hitl/microworld
```

Or via Vercel MCP `create_git_project`:

- repo: `gideonblaauw-creator/cth-data-room-scanner`
- projectName: `cth-hitl-lab`
- rootDirectory: `hitl/microworld`

### Option B — Manual file deploy

```bash
cd hitl/microworld
vercel deploy --prod --name cth-hitl-lab
```

### Disable deployment protection

After first deploy, ensure Vercel Authentication and password protection are **disabled** for production URLs (MCP: `update_project_deployment_protection` with `ssoProtection.enabled: false`).

## Optional demo — review-static

**Not production review.** Static shell + baked BeCaps-style demo findings for walkthroughs only:

- Path: `hitl/review-static/`
- Serve locally: `python3 -m http.server 8766 --directory hitl/review-static`
- Do **not** deploy to public Vercel with real client findings.

## Files

| File | Purpose |
|------|---------|
| `hitl/microworld/vercel.json` | Static host config |
| `hitl/microworld/index.html` | Tabbed microworld (static-first fetch) |
| `hitl/microworld/defaults/*.json` | Bundled VertiGreen gate findings |
| `hitl/review-static/` | Demo-only review shell |
