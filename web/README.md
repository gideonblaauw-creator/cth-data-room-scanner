# CTH Data Room Scanner — React shell (Lane A)

Public-facing React UI for the CTH Data Room Scanner. This shell posts **only** Drive URL + metadata to the Flask+RQ backend on the CTH pod — it never crawls Google Drive in the browser.

**Public URL:** https://apps.cleantechhub.net/dataroom-scanner

## Information architecture

| Route | Purpose |
|-------|---------|
| `/dataroom-scanner/` | Landing |
| `/dataroom-scanner/scan` | Form: Drive URL, company, language, notes |
| `/dataroom-scanner/status/:jobId` | Job status + links to existing HTML/PDF reports |

Report viewer opens the **existing** rendered report (Drive file URL or `/reports/` on the Flask pod). It does not restyle `templates/report.html`.

## Brand

- Palette: `#0C498A` `#B2EEFA` `#9DC384` `#669348` `#69B5FA`
- Fonts: Open Sans / PT Sans
- Tagline: *Inspira. Actúa. Transforma.*
- Footer: CLEANTECHHUB INTERNATIONAL S.L.

## Local preview

```bash
# Terminal 1 — Flask + Redis + worker (from repo root)
docker compose up --build
# or: python -m app.main  (with Redis + worker running)

# Terminal 2 — React dev server
cd web
cp .env.example .env   # optional; Vite proxies /api to :8080 by default
npm install
npm run dev
```

Open http://localhost:5173/dataroom-scanner/

Vite proxies `/api`, `/reports`, and `/health` to `http://127.0.0.1:8080`.

## Production build

```bash
cd web
npm run build
npm run preview   # static preview on :4173/dataroom-scanner/
```

Set `VITE_API_URL` to the Flask scan API base (CTH pod, not Vercel) when building for hosted deploy:

```bash
VITE_API_URL=https://your-cth-pod.example npm run build
```

`VITE_BASE_PATH` defaults to `/dataroom-scanner/` — keep in sync with the path on `apps.cleantechhub.net`.

## Vercel / apps.cleantechhub.net

Deploy from `web/` under the shared `apps.cleantechhub.net` host at path `/dataroom-scanner`. Do **not** use `reportes.cleantechhub.net`.

```bash
cd web
npx vercel --yes
```

Add `https://apps.cleantechhub.net` to `CORS_ORIGINS` on the Flask pod when the shell is live.

## Lovable port

This IA is locked for Lane A. A future Lovable migration waits for Gideon approval on this structure.
