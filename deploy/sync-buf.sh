#!/usr/bin/env bash
# DataPIM — sync XML + images from Windows BUF server via SMB.
#
# Mounts the BUF export share, copies XML + img to the docker inbox volume,
# then unmounts. If the Windows server is offline — exits silently (exit 0).
#
# Prerequisites on Linux:
#   sudo apt install cifs-utils
#
# Credentials file (chmod 600):
#   /opt/datapim/.buf-credentials
#   Contents:
#     username=YOUR_WINDOWS_USER
#     password=YOUR_WINDOWS_PASSWORD
#     domain=WORKGROUP
#
# Setup cron (every hour):
#   0 * * * * /opt/datapim/deploy/sync-buf.sh >> /var/log/datapim-sync.log 2>&1
#
# Usage:
#   sudo bash deploy/sync-buf.sh                     # uses defaults
#   sudo bash deploy/sync-buf.sh --share //10.0.0.5/buf --target /custom/path

set -euo pipefail

# --- Defaults (override via env or flags) ------------------------------------
SMB_SHARE="${BUF_SMB_SHARE:-//WINDOWS-IP/export}"
CREDS_FILE="${BUF_CREDS_FILE:-/opt/datapim/.buf-credentials}"
MOUNT_POINT="${BUF_MOUNT_POINT:-/mnt/buf-export}"
TARGET="${BUF_TARGET:-/var/lib/docker/volumes/datapim_inbox/_data/xml}"

# --- Parse flags -------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --share)  SMB_SHARE="$2";  shift 2 ;;
    --creds)  CREDS_FILE="$2"; shift 2 ;;
    --target) TARGET="$2";     shift 2 ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

# --- Helpers -----------------------------------------------------------------
ts() { date '+%Y-%m-%d %H:%M:%S'; }
log()  { echo "[$(ts)] INFO  $*"; }
warn() { echo "[$(ts)] WARN  $*"; }
err()  { echo "[$(ts)] ERROR $*" >&2; }

# --- Validate ----------------------------------------------------------------
if [[ ! -f "$CREDS_FILE" ]]; then
  err "Credentials file not found: $CREDS_FILE"
  err "Create it with: username=..., password=..., domain=WORKGROUP"
  exit 1
fi

if [[ "$SMB_SHARE" == *"WINDOWS-IP"* ]]; then
  err "SMB_SHARE still has placeholder. Set BUF_SMB_SHARE env or --share flag."
  exit 1
fi

# --- Mount -------------------------------------------------------------------
mkdir -p "$MOUNT_POINT"

log "Mounting $SMB_SHARE"
if ! mount -t cifs "$SMB_SHARE" "$MOUNT_POINT" \
     -o credentials="$CREDS_FILE",ro,iocharset=utf8,vers=3.0 2>/dev/null; then
  warn "Cannot mount $SMB_SHARE (Windows offline or share unavailable). Skipping."
  exit 0
fi

# Ensure we always unmount, even on error.
trap 'umount "$MOUNT_POINT" 2>/dev/null || true' EXIT

# --- Sync --------------------------------------------------------------------
log "Syncing to $TARGET"
mkdir -p "$TARGET"

# XML files
cp_count=0
for f in "$MOUNT_POINT"/*.xml "$MOUNT_POINT"/*.XML; do
  [[ -f "$f" ]] || continue
  cp "$f" "$TARGET/"
  cp_count=$((cp_count + 1))
done
log "Copied $cp_count XML files"

# Images directory
if [[ -d "$MOUNT_POINT/img" ]]; then
  mkdir -p "$TARGET/img"
  rsync -a --delete "$MOUNT_POINT/img/" "$TARGET/img/"
  img_count=$(ls "$TARGET/img/" 2>/dev/null | wc -l)
  log "Synced $img_count images"
elif [[ -d "$MOUNT_POINT/Img" ]]; then
  # Windows case-insensitive — handle both
  mkdir -p "$TARGET/img"
  rsync -a --delete "$MOUNT_POINT/Img/" "$TARGET/img/"
  img_count=$(ls "$TARGET/img/" 2>/dev/null | wc -l)
  log "Synced $img_count images (from Img/)"
else
  warn "No img/ directory found in $SMB_SHARE"
fi

log "Sync complete"
