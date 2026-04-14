# DataPIM — DevOps Preparation Report

**Date:** 2026-04-14
**Agent:** devops (preparation only)
**Status:** COMPLETE

---

## 1. Files created

| Path | Purpose |
|------|---------|
| `deploy/Dockerfile.backend` | Multi-stage prod image (builder + runtime), non-root `app:app` UID 1000, healthcheck, uvicorn workers via env, dev deps stripped. |
| `deploy/Dockerfile.frontend` | Multi-stage `node:22-alpine` → `nginx:alpine`, `VITE_API_URL` baked at build time. |
| `deploy/docker-compose.prod.yml` | Stack: `postgres` (16-alpine, named volume, healthcheck) + `backend` (waits for DB healthy, runs `alembic upgrade head` on boot) + `frontend` + `nginx` (80/443). Internal `datapim_net` bridge, named volumes for postgres/uploads/inbox/certbot. |
| `deploy/nginx-prod.conf` | Reverse proxy with HTTP→HTTPS redirect, ACME webroot location, security headers (HSTS/X-Frame-Options/X-Content-Type-Options/Referrer-Policy), gzip for text+json+xml+svg, `limit_req_zone` 30 r/m on `/export/*`, direct serve of `/uploads/*` from the volume, SPA via `frontend` upstream. |
| `deploy/systemd/datapim.service` | Optional systemd unit wrapping `docker compose up -d`. |
| `deploy/backup.sh` | `pg_dump` → gzip with daily/weekly rotation (defaults 7+4), Sunday auto-promotion, env-overridable target dir. Executable. |
| `deploy/.env.prod.example` | Prod env template — DB creds, JWT, URLs, VITE_API_URL, XML_IMPORT_DIR, optional AI keys. Each var commented. |
| `frontend/nginx.conf` | In-container nginx config: SPA fallback, immutable cache for `/assets/`, `no-store` for `index.html`, `/healthz` endpoint. |
| `frontend/.dockerignore` | Excludes `node_modules`, `dist`, `.env*`, `.git`, editor junk. |
| `.github/workflows/ci.yml` | CI only (no deploy). Jobs: `backend-test` (Postgres service + alembic + pytest), `ruff` (lint+format check), `frontend-test` (tsc + vite build). Concurrency cancels stale runs. |
| `.ai/devops_runbook.md` | Full first-deploy runbook: prereqs, initial setup, certbot bootstrap (http-01 webroot), first deploy, routine ops, backup cron line, rollback (incl. DB restore from gzip), troubleshooting table, useful one-liners. |

## 2. Files modified

| Path | Change |
|------|--------|
| `backend/.dockerignore` | Hardened: blocks `.env*` (allows `.env.example`), `.git*`, caches, editor dirs, logs. |
| `.gitignore` | Added `.env.prod` and `.env.*.local`. |

## 3. Tests run

| Test | Result |
|------|--------|
| `docker compose -f deploy/docker-compose.prod.yml --env-file .env.prod.test config` | OK — yaml parses, all services/volumes/networks resolve. |
| `docker build -f deploy/Dockerfile.backend -t datapim-backend:test backend` | OK — image builds, all deps install. |
| Smoke `docker run datapim-backend:test ...` | OK — runs as `uid=1000(app)`, `uvicorn`+`alembic` on PATH, `app.main` imports cleanly. |
| `docker build -f deploy/Dockerfile.frontend --build-arg VITE_API_URL=https://datapim.example.com -t datapim-frontend:test frontend` | OK — `npm ci` + `vite build` succeed (one harmless "chunk > 500KB" warning from vite — pre-existing, not a deployment issue). |
| `docker run datapim-frontend:test nginx -t` | OK — `frontend/nginx.conf` syntax valid. |
| Test images cleaned up (`docker rmi`) | OK. |

## 4. Things that still require human input

1. **Domain name** — replace `datapim.example.com` in `deploy/nginx-prod.conf` (sed line provided in runbook §2 step 5).
2. **VPS provisioning** — buy/spin up Ubuntu 22.04+ box, point A-record at it.
3. **Secrets generation** — `openssl rand` for `POSTGRES_PASSWORD` (also into `DATABASE_URL`) and `JWT_SECRET`. Paste into `.env.prod` (chmod 600).
4. **SSL certificate** — run the certbot bootstrap recipe from runbook §3 once, then certbot cron handles renewal.
5. **Bootstrap admin user** — fill `DEV_*` in `.env.prod` (auto-seed) or run `python seed.py` after first boot.
6. **Backup cron** — install the cron line from runbook §5 (`/etc/cron.d/datapim-backup`).
7. **(Optional) AI keys** — `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` if AI enrichment is needed at launch.
8. **(Optional) systemd unit** — only if the operator wants `systemctl status datapim` instead of `docker compose ps`.

## 5. What is explicitly NOT done (per task constraints)

- No `docker push` to any registry (images are local-build only).
- No `ssh` to any host.
- No `systemctl start/enable` on the user's machine.
- No edits to `/etc/*` or any system config outside the project.
- No `alembic upgrade/downgrade` on any DB.
- No edits to the real `.env`.
- No `git push` to any remote.
- No `docker compose up` of the prod stack.
- No interaction with the running dev services (uvicorn :8000, vite :5174 untouched).

## 6. Notes for the next human / agent

- Backend image strips `pytest`, `pytest-asyncio`, `httpx`, `ruff` from `requirements.txt` at build time, so the runtime image stays small. If you add new dev-only packages, update the `grep -ivE` line in `deploy/Dockerfile.backend`.
- `nginx-prod.conf` mounts the `uploads_data` volume read-only at `/var/www/uploads` and serves it directly from disk (no proxy round-trip to backend) — fast and offloads the API.
- The compose `backend` service overrides the image CMD with a `sh -c` that runs `alembic upgrade head` first. If you want faster restarts (skipping migration check), comment out that override and migrations will only run when you `exec backend alembic upgrade head` manually.
- Rate limit on `/export/*` is 30 req/min (burst 10). Bump in `nginx-prod.conf` if a partner needs more.
- CI workflow runs alembic against a Postgres service container — if migrations break, the build fails before pytest even starts.
