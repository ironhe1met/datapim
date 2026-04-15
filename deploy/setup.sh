#!/usr/bin/env bash
# DataPIM — one-shot deploy/setup script.
#
# Usage (on a fresh Ubuntu 22 VPS, repo cloned to /opt/datapim):
#   cd /opt/datapim
#   cp deploy/.env.prod.example .env.prod   # edit DOMAIN, ADMIN_EMAIL, DEV_*
#   sudo bash deploy/setup.sh
#
# Re-runnable. Generated secrets are written back to .env.prod once.
# After successful run: https://<DOMAIN>/  is live.

set -euo pipefail

# ---------------------------------------------------------------------------
# 0. Locate project root + .env.prod
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

ENV_FILE="$PROJECT_ROOT/.env.prod"
NGINX_CONF="$SCRIPT_DIR/nginx-prod.conf"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.prod.yml"

log()  { printf "\033[1;36m▶\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m!\033[0m %s\n" "$*"; }
err()  { printf "\033[1;31m✗\033[0m %s\n" "$*" >&2; }
ok()   { printf "\033[1;32m✓\033[0m %s\n" "$*"; }

# ---------------------------------------------------------------------------
# 1. Pre-flight checks
# ---------------------------------------------------------------------------
log "Pre-flight checks"

if ! command -v docker >/dev/null; then
  err "docker not installed. Run: curl -fsSL https://get.docker.com | sudo sh"
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  err "docker compose plugin missing. Install docker-compose-plugin"
  exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
  err ".env.prod not found in $PROJECT_ROOT"
  err "Copy template: cp deploy/.env.prod.example .env.prod"
  exit 1
fi

# Load env (source after stripping CR if file came from Windows).
sed -i 's/\r$//' "$ENV_FILE" 2>/dev/null || true
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# ---------------------------------------------------------------------------
# 2. Validate required vars
# ---------------------------------------------------------------------------
missing=()
[[ -z "${DOMAIN:-}" ]] && missing+=("DOMAIN")
[[ -z "${ADMIN_EMAIL:-}" ]] && missing+=("ADMIN_EMAIL")
[[ -z "${DEV_EMAIL:-}" ]] && missing+=("DEV_EMAIL")
[[ -z "${DEV_PASSWORD:-}" ]] && missing+=("DEV_PASSWORD")
if (( ${#missing[@]} > 0 )); then
  err "Missing in .env.prod: ${missing[*]}"
  exit 1
fi
ok "DOMAIN=$DOMAIN  ADMIN_EMAIL=$ADMIN_EMAIL"

# ---------------------------------------------------------------------------
# 3. Generate secrets if they're still placeholders
# ---------------------------------------------------------------------------
gen_secret() { openssl rand -base64 "$1" | tr -d '\n=+/' | head -c "$1"; }

needs_postgres=0
needs_jwt=0
case "${POSTGRES_PASSWORD:-}" in ''|*CHANGEME*|*FILL_BY_SCRIPT*) needs_postgres=1 ;; esac
case "${JWT_SECRET:-}" in       ''|*CHANGEME*|*FILL_BY_SCRIPT*) needs_jwt=1 ;; esac

if (( needs_postgres )); then
  POSTGRES_PASSWORD="$(gen_secret 32)"
  log "Generated POSTGRES_PASSWORD"
fi
if (( needs_jwt )); then
  JWT_SECRET="$(gen_secret 64)"
  log "Generated JWT_SECRET"
fi

# Always rebuild DATABASE_URL from current values so it stays in sync.
POSTGRES_USER="${POSTGRES_USER:-datapim}"
POSTGRES_DB="${POSTGRES_DB:-datapim}"
DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}"

# Compose URLs from DOMAIN unless explicitly overridden (treat placeholder as unset).
is_placeholder() { [[ -z "$1" || "$1" == *FILL_BY_SCRIPT* || "$1" == *CHANGEME* ]]; }
is_placeholder "${APP_URL:-}"      && APP_URL="https://${DOMAIN}"
is_placeholder "${API_URL:-}"      && API_URL="https://${DOMAIN}"
is_placeholder "${VITE_API_URL:-}" && VITE_API_URL="https://${DOMAIN}"
is_placeholder "${CORS_ORIGINS:-}" && CORS_ORIGINS="https://${DOMAIN}"

# Persist all derived values back to .env.prod (idempotent: replaces or appends).
upsert_env() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" "$ENV_FILE"; then
    # Use | as sed delimiter (URLs / passwords contain /)
    local esc
    esc="$(printf '%s' "$value" | sed -e 's/[\\&|]/\\&/g')"
    sed -i "s|^${key}=.*|${key}=${esc}|" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
}
upsert_env POSTGRES_PASSWORD "$POSTGRES_PASSWORD"
upsert_env JWT_SECRET        "$JWT_SECRET"
upsert_env DATABASE_URL      "$DATABASE_URL"
upsert_env APP_URL           "$APP_URL"
upsert_env API_URL           "$API_URL"
upsert_env VITE_API_URL      "$VITE_API_URL"
upsert_env CORS_ORIGINS      "$CORS_ORIGINS"
chmod 600 "$ENV_FILE"
ok "Secrets persisted to .env.prod (chmod 600)"

# ---------------------------------------------------------------------------
# 4. Substitute DOMAIN into nginx-prod.conf (idempotent)
# ---------------------------------------------------------------------------
log "Configuring nginx for $DOMAIN"
# Backup once.
[[ -f "${NGINX_CONF}.bak" ]] || cp "$NGINX_CONF" "${NGINX_CONF}.bak"
cp "${NGINX_CONF}.bak" "$NGINX_CONF"
sed -i "s/datapim\.example\.com/${DOMAIN}/g" "$NGINX_CONF"
ok "nginx-prod.conf updated"

# ---------------------------------------------------------------------------
# 5. Obtain Let's Encrypt cert (skip if already valid)
# ---------------------------------------------------------------------------
CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"
if [[ -f "${CERT_DIR}/fullchain.pem" ]]; then
  ok "Existing cert found at ${CERT_DIR}"
else
  log "Issuing Let's Encrypt cert for ${DOMAIN}"
  # Stop anything on :80 first (just in case)
  docker stop datapim-acme datapim-nginx 2>/dev/null || true
  # Use certbot in --standalone mode — port 80 must be free.
  if ! ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE ':80$'; then
    docker run --rm \
      -p 80:80 \
      -v /etc/letsencrypt:/etc/letsencrypt \
      certbot/certbot:latest \
      certonly --standalone \
        --non-interactive --agree-tos \
        --email "$ADMIN_EMAIL" \
        -d "$DOMAIN"
    ok "Cert issued"
  else
    err "Port 80 is busy. Free it (sudo ss -ltnp | grep :80) and re-run."
    exit 1
  fi
fi

# ---------------------------------------------------------------------------
# 6. Build images + bring stack up
# ---------------------------------------------------------------------------
log "Building images (this may take a few minutes on first run)"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build

log "Starting stack"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

# ---------------------------------------------------------------------------
# 7. Wait for postgres + backend health
# ---------------------------------------------------------------------------
log "Waiting for postgres healthy..."
for _ in $(seq 1 30); do
  if docker exec datapim-postgres pg_isready -U "$POSTGRES_USER" >/dev/null 2>&1; then
    ok "postgres ready"
    break
  fi
  sleep 2
done

log "Waiting for backend health..."
for _ in $(seq 1 60); do
  if curl -fs http://localhost:8000/health >/dev/null 2>&1; then
    ok "backend ready"
    break
  fi
  sleep 2
done

# ---------------------------------------------------------------------------
# 8. Run migrations (alembic) + seed admin
# ---------------------------------------------------------------------------
log "Running alembic migrations"
docker exec datapim-backend alembic upgrade head

if [[ -n "${DEV_EMAIL}" && -n "${DEV_PASSWORD}" ]]; then
  log "Seeding admin user (${DEV_EMAIL})"
  docker exec \
    -e DEV_EMAIL="$DEV_EMAIL" \
    -e DEV_PASSWORD="$DEV_PASSWORD" \
    -e DEV_NAME="${DEV_NAME:-Admin}" \
    datapim-backend python seed.py || warn "seed.py exited non-zero (admin may already exist)"
fi

# ---------------------------------------------------------------------------
# 9. Verify HTTPS endpoint
# ---------------------------------------------------------------------------
log "Verifying HTTPS"
if curl -fsk "https://${DOMAIN}/health" >/dev/null 2>&1; then
  ok "https://${DOMAIN}/health OK"
else
  warn "https://${DOMAIN}/health did not respond — check 'docker compose logs nginx'"
fi

# ---------------------------------------------------------------------------
# 10. Summary
# ---------------------------------------------------------------------------
cat <<EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 DataPIM is live  🎉
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Frontend:        https://${DOMAIN}/
 API docs:        https://${DOMAIN}/api/docs
 Public XML:      https://${DOMAIN}/export/products.xml
 Admin login:     ${DEV_EMAIL}
                  (password from .env.prod DEV_PASSWORD)

 Useful commands (run from $PROJECT_ROOT):
   docker compose -f deploy/docker-compose.prod.yml ps
   docker compose -f deploy/docker-compose.prod.yml logs -f backend
   docker compose -f deploy/docker-compose.prod.yml restart backend

 Cert auto-renew:  add to crontab —
   0 3 * * * cd $PROJECT_ROOT && docker run --rm -v /etc/letsencrypt:/etc/letsencrypt certbot/certbot renew --quiet && docker compose -f deploy/docker-compose.prod.yml exec nginx nginx -s reload

 Backup DB:        bash deploy/backup.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
