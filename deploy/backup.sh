#!/usr/bin/env bash
# DataPIM — postgres backup with daily + weekly rotation.
#
# Defaults (override via env):
#   BACKUP_DIR=/var/backups/datapim
#   PG_CONTAINER=datapim-postgres
#   PG_USER=$(POSTGRES_USER from .env.prod)   fallback: postgres
#   PG_DB=$(POSTGRES_DB   from .env.prod)     fallback: datapim
#   KEEP_DAILY=7
#   KEEP_WEEKLY=4
#
# Cron example (daily 03:15):
#   15 3 * * *  /opt/datapim/deploy/backup.sh >> /var/log/datapim-backup.log 2>&1
#
# Restore:
#   gunzip -c /var/backups/datapim/daily/datapim-YYYY-MM-DD-HHMM.sql.gz \
#     | docker exec -i datapim-postgres psql -U postgres -d datapim

set -euo pipefail

# --- Load .env.prod if present (for POSTGRES_USER / POSTGRES_DB) -----------
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${PROJECT_ROOT}/.env.prod" ]]; then
    # shellcheck disable=SC1090,SC1091
    set -a; . "${PROJECT_ROOT}/.env.prod"; set +a
fi

BACKUP_DIR="${BACKUP_DIR:-/var/backups/datapim}"
PG_CONTAINER="${PG_CONTAINER:-datapim-postgres}"
PG_USER="${POSTGRES_USER:-postgres}"
PG_DB="${POSTGRES_DB:-datapim}"
KEEP_DAILY="${KEEP_DAILY:-7}"
KEEP_WEEKLY="${KEEP_WEEKLY:-4}"

DAILY_DIR="${BACKUP_DIR}/daily"
WEEKLY_DIR="${BACKUP_DIR}/weekly"
mkdir -p "${DAILY_DIR}" "${WEEKLY_DIR}"

TIMESTAMP="$(date +%Y-%m-%d-%H%M)"
DAILY_FILE="${DAILY_DIR}/datapim-${TIMESTAMP}.sql.gz"

echo "[backup] $(date -Iseconds) starting pg_dump → ${DAILY_FILE}"

# Stream straight from the container, gzip on the host, never touch disk in plain text.
docker exec -t "${PG_CONTAINER}" \
    pg_dump --clean --if-exists --no-owner --no-privileges \
            -U "${PG_USER}" -d "${PG_DB}" \
    | gzip -9 > "${DAILY_FILE}.tmp"
mv "${DAILY_FILE}.tmp" "${DAILY_FILE}"

SIZE="$(du -h "${DAILY_FILE}" | cut -f1)"
echo "[backup] wrote ${DAILY_FILE} (${SIZE})"

# --- Promote to weekly on Sundays ------------------------------------------
if [[ "$(date +%u)" == "7" ]]; then
    WEEKLY_FILE="${WEEKLY_DIR}/datapim-${TIMESTAMP}.sql.gz"
    cp -p "${DAILY_FILE}" "${WEEKLY_FILE}"
    echo "[backup] promoted to ${WEEKLY_FILE}"
fi

# --- Rotation ---------------------------------------------------------------
# Keep newest N files, delete the rest.
prune() {
    local dir="$1" keep="$2"
    # ls -1t orders by mtime desc; tail -n +N+1 lists the surplus.
    # shellcheck disable=SC2012
    ls -1t "${dir}"/*.sql.gz 2>/dev/null | tail -n +"$((keep + 1))" | while read -r old; do
        echo "[backup] pruning ${old}"
        rm -f "${old}"
    done
}

prune "${DAILY_DIR}"  "${KEEP_DAILY}"
prune "${WEEKLY_DIR}" "${KEEP_WEEKLY}"

echo "[backup] $(date -Iseconds) done"
