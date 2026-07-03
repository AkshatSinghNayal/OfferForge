# Deployment Guide

Exact ordered steps to go from a clean clone to a running production deployment.
Follow them in order — each step depends on values from the previous one.

---

## Prerequisites

- GitHub repo with this code pushed to `main`
- Render account (free tier works; upgrade for always-on)
- Vercel account (free tier)
- Google Cloud Console project with OAuth 2.0 credentials
- Cloudinary account (free tier for resume storage)

---

## Step 1 — Create the Render PostgreSQL database

1. Go to [render.com](https://render.com) → Dashboard → **New** → **PostgreSQL**.
2. Name: `placement-tracker-db`
3. Database name: `placement_tracker`, User: `placement`
4. Plan: Free (or Starter for production)
5. Region: Oregon (or nearest to your users)
6. Click **Create Database** and wait for it to become **Available**.
7. Copy the **Internal Database URL** — you'll need it in Step 2.
   > ⚠️ The URL Render gives you starts with `postgres://`. The backend needs
   > `postgresql+asyncpg://`. Replace the scheme manually:
   > `postgres://` → `postgresql+asyncpg://`

---

## Step 2 — Deploy the backend on Render

### Option A — Blueprint (recommended, uses render.yaml)

1. Dashboard → **New** → **Blueprint**
2. Connect your GitHub repo
3. Render reads `render.yaml` and creates the services
4. In the **Environment** tab for `placement-tracker-api`, set the `sync: false` variables:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | `postgresql+asyncpg://placement:<password>@<host>/<db>` (from Step 1) |
| `FRONTEND_URL` | `https://your-app.vercel.app` (placeholder — update in Step 5) |
| `BACKEND_URL` | `https://placement-tracker-api.onrender.com` (your Render URL) |
| `GOOGLE_CLIENT_ID` | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud Console |
| `CLOUDINARY_CLOUD_NAME` | From Cloudinary dashboard |
| `CLOUDINARY_API_KEY` | From Cloudinary dashboard |
| `CLOUDINARY_API_SECRET` | From Cloudinary dashboard |

5. Click **Deploy** → wait for the deploy to go green.

### Option B — Manual web service

1. Dashboard → **New** → **Web Service**
2. Connect your GitHub repo, root directory: `backend`
3. Runtime: **Docker**, Dockerfile path: `./Dockerfile`
4. Set all env vars from the table above.
5. Health check path: `/api/v1/health`

---

## Step 3 — Verify the backend

```bash
curl https://placement-tracker-api.onrender.com/api/v1/health
# Expected: {"status":"ok","db":"ok"}
```

If `db` is `"error"`, the `DATABASE_URL` is wrong — double-check the scheme and credentials.

---

## Step 4 — Deploy the frontend on Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import your GitHub repo
3. **Root Directory**: `frontend`
4. Framework preset: **Other** (or Vite)
5. Build command: `npm run build`
6. Output directory: `dist`
7. Add environment variable:

| Key | Value |
|-----|-------|
| `VITE_API_URL` | `https://placement-tracker-api.onrender.com` |

8. Click **Deploy** and wait for the green checkmark.
9. Copy your Vercel deployment URL (e.g. `https://placement-tracker.vercel.app`).

---

## Step 5 — Update FRONTEND_URL on Render

1. Render Dashboard → `placement-tracker-api` → **Environment**
2. Update `FRONTEND_URL` to your Vercel URL: `https://placement-tracker.vercel.app`
3. **Save** — Render will automatically redeploy.

> This is critical for CORS. The backend only allows requests from `FRONTEND_URL`.
> Until this is set correctly, the browser will get `403` or a CORS error on every API call.

---

## Step 6 — Update Google OAuth authorized URIs

In [Google Cloud Console](https://console.cloud.google.com):

1. APIs & Services → Credentials → your OAuth 2.0 Client ID
2. **Authorized JavaScript origins**: add `https://placement-tracker.vercel.app`
3. **Authorized redirect URIs**: add `https://placement-tracker-api.onrender.com/api/v1/auth/google/callback`
4. Save.

Without Step 6, Google sign-in will fail with `redirect_uri_mismatch`.

---

## Step 7 — Smoke test the full stack

```bash
# 1. Health check
curl https://placement-tracker-api.onrender.com/api/v1/health

# 2. Sign up a test user
curl -s -X POST https://placement-tracker-api.onrender.com/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123","full_name":"Test User"}'

# 3. Log in
curl -s -X POST https://placement-tracker-api.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'
```

Then open the Vercel URL in a browser and verify:
- [ ] Login page loads
- [ ] Sign up works end-to-end
- [ ] Dashboard loads after login (no CORS errors in browser devtools)
- [ ] Theme toggle works
- [ ] ⌘K command palette opens and search returns results

---

## What to check post-deploy for CORS (if you can't verify locally)

1. Open browser devtools → Network tab → filter by XHR/Fetch
2. Log in and check the `POST /api/v1/auth/login` request
3. The response should include:
   ```
   Access-Control-Allow-Origin: https://your-vercel-url.vercel.app
   Access-Control-Allow-Credentials: true
   ```
4. If you see `Access-Control-Allow-Origin: *` or no CORS header, `FRONTEND_URL` on Render is wrong.
5. If you see a CORS error, the `FRONTEND_URL` env var on Render doesn't match the exact Vercel URL (including protocol, no trailing slash).

---

## Local development

```bash
# 1. Copy and fill the env file
cp backend/.env.example .env
# Fill in JWT secrets, Google OAuth, Cloudinary values

# 2. Start everything
docker-compose up --build

# Backend:  http://localhost:8000
# Frontend: http://localhost:5173
# API docs: http://localhost:8000/docs
```

All services start from a single `docker-compose up`. Migrations run automatically.

---

## Environment variable reference

| Variable | Required | Where set | Notes |
|----------|----------|-----------|-------|
| `DATABASE_URL` | Yes | Render / .env | Must use `postgresql+asyncpg://` scheme |
| `JWT_SECRET_KEY` | Yes | Render (auto-generated) / .env | Min 32 chars in prod |
| `JWT_REFRESH_SECRET_KEY` | Yes | Render (auto-generated) / .env | Min 32 chars in prod |
| `FRONTEND_URL` | Yes | Render | Exact Vercel URL, no trailing slash |
| `BACKEND_URL` | Yes | Render | Exact Render URL, no trailing slash |
| `GOOGLE_CLIENT_ID` | OAuth only | Render / .env | Leave empty to disable Google login |
| `GOOGLE_CLIENT_SECRET` | OAuth only | Render / .env | |
| `CLOUDINARY_CLOUD_NAME` | Resume upload | Render / .env | Leave empty to disable resume upload |
| `CLOUDINARY_API_KEY` | Resume upload | Render / .env | |
| `CLOUDINARY_API_SECRET` | Resume upload | Render / .env | |
| `VITE_API_URL` | Yes (Vercel) | Vercel env vars | Baked in at build time |
