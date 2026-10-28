#!/usr/bin/env bash
# Safe Bandit City update from GitHub. Run as root on the VPS.
set -Eeuo pipefail
umask 077

APP_DIR="${APP_DIR:-/root/Bandit-City}"
REPO_URL="${REPO_URL:-https://github.com/shelabin2017-ui/Bandit-City.git}"
REF="${1:-main}"
SERVICE="${SERVICE:-bandit-city.service}"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
BACKUP_ROOT="/var/backups/bandit-city"
BACKUP_DIR="$BACKUP_ROOT/deploy-$STAMP"
TMP_DIR="$(mktemp -d /tmp/bandit-city-update.XXXXXX)"
HAD_SERVICE=0
if systemctl is-active --quiet "$SERVICE"; then HAD_SERVICE=1; fi

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

if [[ "$(id -u)" -ne 0 ]]; then
  echo "ERROR: run this script as root (sudo)." >&2
  exit 1
fi
if [[ ! -d "$APP_DIR" || ! -f "$APP_DIR/run.py" ]]; then
  echo "ERROR: expected existing project at $APP_DIR; refusing to deploy." >&2
  exit 1
fi
for cmd in git rsync tar python3 systemctl; do
  command -v "$cmd" >/dev/null || { echo "ERROR: missing command: $cmd" >&2; exit 1; }
done
mkdir -p "$BACKUP_DIR"
echo "[1/6] Backing up current project to $BACKUP_DIR"
tar -czf "$BACKUP_DIR/project.tar.gz" -C "$APP_DIR" \
  --exclude='./.git' --exclude='./.venv' --exclude='./__pycache__' .
cp -a "$APP_DIR/.env" "$BACKUP_DIR/.env" 2>/dev/null || true
cp -a "$APP_DIR/bandit.db" "$BACKUP_DIR/bandit.db" 2>/dev/null || true

echo "[2/6] Downloading ref '$REF' from GitHub"
git clone --depth 1 --branch "$REF" "$REPO_URL" "$TMP_DIR/source"

if [[ -f "$TMP_DIR/source/.env" || -f "$TMP_DIR/source/bandit.db" ]]; then
  echo "ERROR: source unexpectedly contains runtime secrets/database; refusing to copy them." >&2
  exit 1
fi

echo "[3/6] Updating code while preserving .env, bandit.db and virtualenv"
rsync -a "$TMP_DIR/source/" "$APP_DIR/" \
  --exclude='.git/' --exclude='.env' --exclude='bandit.db' --exclude='.venv/' \
  --exclude='__pycache__/' --exclude='*.pyc' --exclude='*.db' --exclude='*.sqlite*'

PYTHON="$APP_DIR/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: project virtualenv not found at $PYTHON; restoring previous project." >&2
  tar -xzf "$BACKUP_DIR/project.tar.gz" -C "$APP_DIR"
  exit 1
fi

rollback() {
  local code=$?
  trap - ERR
  echo "ERROR: update validation/startup failed (exit $code). Rolling back project files and runtime database/config backup." >&2
  systemctl stop "$SERVICE" >/dev/null 2>&1 || true
  tar -xzf "$BACKUP_DIR/project.tar.gz" -C "$APP_DIR" || true
  [[ ! -f "$BACKUP_DIR/.env" ]] || cp -a "$BACKUP_DIR/.env" "$APP_DIR/.env"
  [[ ! -f "$BACKUP_DIR/bandit.db" ]] || cp -a "$BACKUP_DIR/bandit.db" "$APP_DIR/bandit.db"
  if [[ "$HAD_SERVICE" -eq 1 ]]; then systemctl start "$SERVICE" || true; fi
  exit "$code"
}
trap rollback ERR

echo "[4/6] Running syntax and regression checks"
"$PYTHON" -m compileall -q "$APP_DIR"
if [[ -d "$APP_DIR/tests" ]]; then
  (cd "$APP_DIR" && "$PYTHON" -m unittest discover -s tests -v)
fi
if [[ -f "$APP_DIR/selftest.py" ]]; then
  (cd "$APP_DIR" && "$PYTHON" selftest.py)
fi

echo "[5/6] Restarting service"
systemctl restart "$SERVICE"
sleep 3
systemctl is-active --quiet "$SERVICE"
if systemctl show "$SERVICE" -p NRestarts --value | grep -Eq '^[1-9][0-9]*$'; then
  echo "WARNING: systemd reports restarts; inspect journal before considering deployment healthy." >&2
fi

echo "[6/6] Update complete"
echo "Ref: $REF"
echo "Backup: $BACKUP_DIR"
echo "Config/database preserved: .env and bandit.db"
systemctl --no-pager --full status "$SERVICE" | head -n 18
