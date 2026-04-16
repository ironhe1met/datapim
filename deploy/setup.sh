#!/usr/bin/env bash
# DataPIM — install on internal server.
#
# Usage:
#   cd /opt/datapim
#   cp deploy/.env.prod.example .env.prod && nano .env.prod
#   sudo bash deploy/setup.sh
#
# No SSL — SSL terminates on external proxy VPS (see proxy-setup.sh).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

ENV_FILE="$PROJECT_ROOT/.env.prod"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.prod.yml"

log()  { printf "\033[1;36m▶\033[0m %s\n" "$*"; }
ok()   { printf "\033[1;32m✓\033[0m %s\n" "$*"; }
err()  { printf "\033[1;31m✗\033[0m %s\n" "$*" >&2; }

# --- 1. Pre-flight ---------------------------------------------------------
log "Pre-flight checks"
command -v docker >/dev/null || { err "docker not found. Install: curl -fsSL https://get.docker.com | sudo sh"; exit 1; }
docker compose version >/dev/null 2>&1 || { err "docker compose plugin missing"; exit 1; }
[[ -f "$ENV_FILE" ]] || { err ".env.prod not found. cp deploy/.env.prod.example .env.prod"; exit 1; }

sed -i 's/\r$//' "$ENV_FILE" 2>/dev/null || true
set -a; source "$ENV_FILE"; set +a

# --- 2. Required vars ------------------------------------------------------
missing=()
[[ -z "${DOMAIN:-}" ]] && missing+=("DOMAIN")
[[ -z "${DEV_EMAIL:-}" ]] && missing+=("DEV_EMAIL")
[[ -z "${DEV_PASSWORD:-}" ]] && missing+=("DEV_PASSWORD")
(( ${#missing[@]} > 0 )) && { err "Missing in .env.prod: ${missing[*]}"; exit 1; }
ok "DOMAIN=$DOMAIN"

# --- 3. Generate secrets if needed ------------------------------------------
gen_secret() { openssl rand -base64 "$1" | tr -d '\n=+/' | head -c "$1"; }
is_placeholder() { [[ -z "$1" || "$1" == *FILL_BY_SCRIPT* || "$1" == *CHANGEME* ]]; }

if is_placeholder "${POSTGRES_PASSWORD:-}"; then
  POSTGRES_PASSWORD="$(gen_secret 32)"
  log "Generated POSTGRES_PASSWORD"
fi
if is_placeholder "${JWT_SECRET:-}"; then
  JWT_SECRET="$(gen_secret 64)"
  log "Generated JWT_SECRET"
fi

POSTGRES_USER="${POSTGRES_USER:-datapim}"
POSTGRES_DB="${POSTGRES_DB:-datapim}"
DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}"
is_placeholder "${APP_URL:-}"      && APP_URL="https://${DOMAIN}"
is_placeholder "${API_URL:-}"      && API_URL="https://${DOMAIN}"
is_placeholder "${VITE_API_URL:-}" && VITE_API_URL="https://${DOMAIN}"
is_placeholder "${CORS_ORIGINS:-}" && CORS_ORIGINS="https://${DOMAIN}"

# Persist
upsert_env() {
  local key="$1" value="$2"
  local esc; esc="$(printf '%s' "$value" | sed -e 's/[\\&|]/\\&/g')"
  if grep -q "^${key}=" "$ENV_FILE"; then
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
ok "Secrets in .env.prod"

# --- 4. Build + start -------------------------------------------------------
log "Building images (first run takes a few minutes)"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build

log "Starting stack"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

# --- 5. Wait healthy -------------------------------------------------------
log "Waiting for postgres..."
for _ in $(seq 1 30); do
  docker exec datapim-postgres pg_isready -U "$POSTGRES_USER" >/dev/null 2>&1 && break
  sleep 2
done
ok "postgres ready"

log "Waiting for backend..."
LISTEN_PORT="${LISTEN_PORT:-3000}"
for _ in $(seq 1 60); do
  curl -fs "http://localhost:${LISTEN_PORT}/health" >/dev/null 2>&1 && break
  sleep 2
done
ok "backend ready"

# --- 6. Seed admin ----------------------------------------------------------
if [[ -n "${DEV_EMAIL:-}" && -n "${DEV_PASSWORD:-}" ]]; then
  log "Seeding admin (${DEV_EMAIL})"
  docker exec datapim-backend python seed.py || true
fi

# --- 7. Done ----------------------------------------------------------------
cat <<EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 DataPIM started on port ${LISTEN_PORT}  (HTTP, no SSL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Local test:  curl http://localhost:${LISTEN_PORT}/health
 Admin:       ${DEV_EMAIL}
 Domain:      ${DOMAIN} (configure on proxy VPS)

 Next step:   on your proxy VPS run
              sudo bash deploy/proxy-setup.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
