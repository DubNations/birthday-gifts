# Vercel deployment layout

This repository is now deployable from the repository root in Vercel.

## Directory layout

```text
birthday-gifts/
├── api/
│   └── index.py              # Vercel Python function entrypoint, imports backend.app.main:app
├── backend/
│   ├── app/                  # Shared FastAPI application code
│   └── requirements.txt      # Backend runtime dependencies
├── frontend/
│   ├── src/                  # React/Vite source
│   └── package.json          # Frontend dependencies and build scripts
├── requirements.txt          # Root Vercel Python dependency proxy
├── package.json              # Root Vercel build script wrapper
├── vercel.json               # Vercel build, function, and rewrite config
└── .vercelignore             # Keeps local/runtime-only files out of Vercel uploads
```

## Required Vercel environment variables

Set these in **Vercel Project Settings → Environment Variables** before opening the deployed app:

| Variable | Required | Notes |
| --- | --- | --- |
| `ADMIN_PASSWORD` | Yes | Administrator login password. The backend rejects missing or insecure default passwords. |
| `ADMIN_TOKEN_SECRET` | Recommended | Signing secret for administrator bearer tokens. If omitted, the password is used as the signing secret. |
| `DATABASE_URL` | Yes for persistence | Use a hosted PostgreSQL connection string for real deployments. Vercel serverless filesystems are ephemeral, so SQLite is not suitable for shared production inventory. |
| `CORS_ORIGINS` | Optional for same-origin Vercel deploy | Leave empty when the frontend calls same-origin `/api`. Set comma-separated origins if another domain calls the API. |
| `VITE_API_BASE_URL` | Optional | Leave empty for the bundled Vercel deployment. Set only if the frontend should call a separate external API origin. |
| `LOCK_TIMEOUT_MINUTES` | Optional | Defaults to `15`. |
| `MAX_REGRET_CHANCES` | Optional | Defaults to `1`. |

## How Vercel serves the app

- `npm run vercel-build` builds `frontend/dist`.
- Static frontend assets are served from `frontend/dist`.
- `/api/*` is rewritten to `api/index.py`, which exposes the existing FastAPI app.
- All other paths rewrite to `index.html` so the React SPA can handle browser refreshes.

## Local checks before deploying

```bash
npm run build
ADMIN_PASSWORD='replace-me' DATABASE_URL='sqlite:////tmp/birthday-gifts-local.db' python -c "from api.index import app; print(app.title)"
```
