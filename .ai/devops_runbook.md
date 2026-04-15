# DataPIM — Deployment Runbook

> **TL;DR — first deploy in 4 commands** (after VPS + DNS A-record exist):
>
> ```bash
> sudo mkdir -p /opt/datapim && sudo chown $USER:$USER /opt/datapim
> git clone <repo-url> /opt/datapim && cd /opt/datapim
> cp deploy/.env.prod.example .env.prod && nano .env.prod   # edit DOMAIN, ADMIN_EMAIL, DEV_*
> sudo bash deploy/setup.sh
> ```
>
> The script generates secrets, gets the Let's Encrypt cert, builds images,
> brings the stack up, runs migrations, and seeds the admin user. Re-runnable.

Step-by-step guide for a human operator deploying DataPIM to a fresh VPS for
the first time, plus routine ops procedures.

> **Audience:** sysadmin / developer with basic Linux + Docker knowledge.
> **Source of truth for infra files:** `deploy/` in this repo.

---

## 1. Prerequisites

| Item | Minimum |
|------|---------|
| OS | Ubuntu 22.04 LTS (or newer) |
| RAM | 2 GB (4 GB recommended) |
| Disk | 20 GB SSD |
| CPU | 1 vCPU (2 recommended) |
| Network | Public IPv4, ports 80/443 open |
| Domain | A-record pointing at the VPS IP |
| Software | `docker` (>= 24) + `docker compose` plugin, `git`, `curl` |

Install Docker (Ubuntu):

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# log out / log in so the group takes effect
```

---

## 2. Initial setup

```bash
# 1. SSH to the VPS as a non-root user with sudo
ssh deploy@your-vps

# 2. Clone the repo (use an SSH deploy key if private)
sudo mkdir -p /opt/datapim && sudo chown $USER:$USER /opt/datapim
git clone <repo-url> /opt/datapim
cd /opt/datapim

# 3. Create the prod env file from the template
cp deploy/.env.prod.example .env.prod
chmod 600 .env.prod

# 4. Generate strong secrets and edit .env.prod
openssl rand -base64 24   # → POSTGRES_PASSWORD
openssl rand -base64 48   # → JWT_SECRET
nano .env.prod
#   - set APP_URL / API_URL / VITE_API_URL / CORS_ORIGINS to https://your.domain
#   - paste POSTGRES_PASSWORD into both POSTGRES_PASSWORD and DATABASE_URL
#   - paste JWT_SECRET
#   - (optional) set ANTHROPIC_API_KEY / OPENAI_API_KEY

# 5. Update the domain in the nginx config
sed -i 's/datapim.example.com/your.domain/g' deploy/nginx-prod.conf
```

---

## 3. SSL certificate (Let's Encrypt, http-01 webroot)

```bash
# 1. Bring the stack up on port 80 only (without SSL) so certbot can verify.
#    Temporarily comment out the `listen 443 ssl` server block in
#    deploy/nginx-prod.conf, OR use the bootstrap shortcut below.

# Bootstrap shortcut: run nginx alone with a minimal config that only serves
# the ACME challenge.  Faster and cleaner than editing nginx-prod.conf twice.
docker run --rm -d --name datapim-acme \
    -p 80:80 \
    -v /etc/letsencrypt:/etc/letsencrypt \
    -v /var/www/certbot:/var/www/certbot \
    nginx:alpine \
    sh -c "echo 'server { listen 80; location /.well-known/acme-challenge/ { root /var/www/certbot; } location / { return 200 ok; } }' \
           > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"

# 2. Issue the cert
sudo apt-get install -y certbot
sudo certbot certonly --webroot -w /var/www/certbot \
    -d your.domain \
    --email you@example.com --agree-tos --no-eff-email

# 3. Tear down the bootstrap
docker stop datapim-acme
```

The cert now lives at `/etc/letsencrypt/live/your.domain/{fullchain,privkey}.pem`
and is mounted read-only into the prod nginx container.

**Renewal (cron):**

```cron
# /etc/cron.d/datapim-certbot
0 4 * * *  root  certbot renew --quiet --deploy-hook "docker exec datapim-nginx nginx -s reload"
```

---

## 4. First deploy

```bash
cd /opt/datapim

# Build images locally (no registry push required)
docker compose -f deploy/docker-compose.prod.yml --env-file .env.prod build

# Start the stack
docker compose -f deploy/docker-compose.prod.yml --env-file .env.prod up -d

# Watch logs until backend reports "app_startup"
docker compose -f deploy/docker-compose.prod.yml logs -f backend

# Smoke test
curl -fsS https://your.domain/health
```

The backend container runs `alembic upgrade head` automatically before
starting uvicorn, so the DB schema is always in sync with the deployed code.

**Create the first admin user** (only if you didn't set `DEV_*` vars):

```bash
docker compose -f deploy/docker-compose.prod.yml exec backend python seed.py
# OR via SQL
docker compose -f deploy/docker-compose.prod.yml exec postgres \
    psql -U datapim -d datapim -c "INSERT INTO users ..."
```

---

## 5. Routine operations

```bash
COMPOSE="docker compose -f deploy/docker-compose.prod.yml --env-file .env.prod"

# Restart a service
$COMPOSE restart backend

# Tail logs
$COMPOSE logs -f backend
$COMPOSE logs -f nginx

# Apply a new migration after `git pull`
$COMPOSE exec backend alembic upgrade head

# Redeploy after `git pull`
$COMPOSE build backend frontend
$COMPOSE up -d

# Take a manual backup
bash deploy/backup.sh

# Open a shell in the backend
$COMPOSE exec backend sh
```

### Backup cron

```cron
# /etc/cron.d/datapim-backup
15 3 * * *  root  /opt/datapim/deploy/backup.sh >> /var/log/datapim-backup.log 2>&1
```

Backups land in `/var/backups/datapim/{daily,weekly}/datapim-YYYY-MM-DD-HHMM.sql.gz`.
Rotation: 7 daily + 4 weekly (override via `KEEP_DAILY` / `KEEP_WEEKLY` env vars).

---

## 6. Rollback

```bash
COMPOSE="docker compose -f deploy/docker-compose.prod.yml --env-file .env.prod"

# 1. Stop the broken backend
$COMPOSE stop backend

# 2. Roll the code back
cd /opt/datapim
git log --oneline -10
git checkout <previous-good-sha>

# 3. Restore the DB if a migration corrupted it
LATEST=$(ls -1t /var/backups/datapim/daily/*.sql.gz | head -1)
gunzip -c "$LATEST" \
    | $COMPOSE exec -T postgres psql -U datapim -d datapim

# 4. Rebuild and bring everything back
$COMPOSE build backend
$COMPOSE up -d
```

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `backend` container restart-loops | DB not ready, or `alembic upgrade head` failed | `docker compose logs backend` — fix migration, then `docker compose up -d` |
| `502 Bad Gateway` from nginx | backend down, or `proxy_pass` upstream wrong | `docker compose ps`; verify `backend:8000` reachable from nginx container |
| `503` on `/api/auth/login` | `JWT_SECRET` empty | check `.env.prod`, restart backend |
| XML import hangs silently | known issue (see `.ai/problems.md`): wrapped in try/except + check `import_logs` table | `SELECT * FROM import_logs ORDER BY id DESC LIMIT 5;` |
| AI enrichment fails for all providers | API keys missing/invalid | check `.env.prod`, test with `curl` |
| `pg_isready` healthcheck fails | wrong `POSTGRES_PASSWORD`, or volume corrupted | check creds; if volume corrupt, restore from backup (section 6) |
| `Permission denied` on `/app/uploads` | host UID mismatch on bind-mount | use named volume (default), or `chown 1000:1000` the host dir |
| 429 on `/export/*` | rate limit (30 req/min) | expected; tune `limit_req_zone` in `nginx-prod.conf` if your partner needs more |
| SSL cert expired | certbot cron not running | `sudo certbot renew --dry-run`; reload nginx |

---

## 8. Useful one-liners

```bash
# DB shell
$COMPOSE exec postgres psql -U datapim -d datapim

# Show env actually seen by a container
$COMPOSE exec backend env | sort

# Force-recreate just one service
$COMPOSE up -d --force-recreate --no-deps backend

# Disk usage by docker objects
docker system df

# Prune dangling images after a redeploy
docker image prune -f
```

---

## 9. What this runbook deliberately does NOT cover

- Multi-host / HA deployments (single-VPS only)
- Blue/green or canary releases
- Centralised log shipping (use `docker compose logs` or `journalctl`)
- Off-site backup replication (add `rclone` / `rsync` on top of `backup.sh`)
- Automated CI/CD deploy — CI in `.github/workflows/ci.yml` builds & tests only
