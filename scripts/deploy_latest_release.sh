#!/usr/bin/env bash
set -Eeuo pipefail
# Safe deploy of the latest published GitHub Release for Bandit City.
REPO="${BANDIT_REPO:-shelabin2017-ui/Bandit-City}"
APP_DIR="${BANDIT_APP_DIR:-/root/Bandit-City}"
SERVICE="${BANDIT_SERVICE:-bandit-city.service}"
VENV="${BANDIT_VENV:-/root/Bandit-City-runtime-venv}"
STATE_DIR="${BANDIT_STATE_DIR:-/var/backups/bandit-city}"
LOG_DIR="${BANDIT_LOG_DIR:-/var/log/bandit-city}"
NOW="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_FILE="$LOG_DIR/deploy-$NOW.log"
mkdir -p "$LOG_DIR" "$STATE_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1
say(){ printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*"; }
fail(){ say "ERROR: $*"; exit 1; }
for cmd in curl jq unzip tar rsync python3 systemctl; do command -v "$cmd" >/dev/null || fail "Required command missing: $cmd"; done
[ "$(id -u)" -eq 0 ] || fail "Run as root (sudo -i, then execute script)."
[ -d "$APP_DIR" ] || fail "App directory missing: $APP_DIR"
[ -f "$APP_DIR/.env" ] || fail "Existing .env not found; refusing deployment."
[ -f "$APP_DIR/bandit.db" ] || fail "Existing bandit.db not found; refusing deployment."
mkdir -p "$STATE_DIR"
say "Querying latest published release: $REPO"
API="https://api.github.com/repos/$REPO/releases/latest"
curl --fail --silent --show-error --location --retry 3 "$API" -o "/tmp/bandit-release-$NOW.json" || fail "GitHub Releases API request failed."
TAG="$(jq -r '.tag_name // empty' "/tmp/bandit-release-$NOW.json")"
[ -n "$TAG" ] && [ "$TAG" != "null" ] || fail "No published release tag found. Publish a vX.Y.Z release first."
if [ -f "$APP_DIR/VERSION.txt" ] && [ "$(cat "$APP_DIR/VERSION.txt")" = "$TAG" ]; then
  say "Already running release $TAG; nothing to do."
  exit 0
fi
URL="$(jq -r '[.assets[] | select(.name == "bandit-city-release.zip")][0].browser_download_url // empty' "/tmp/bandit-release-$NOW.json")"
[ -n "$URL" ] || fail "Release $TAG has no bandit-city-release.zip asset; refusing to deploy source archive."
say "Latest release: $TAG"
TMP="$(mktemp -d /tmp/bandit-deploy.XXXXXX)"
BACKUP="$STATE_DIR/pre-$TAG-$NOW.tar.gz"
MUTATED=0
rollback(){
  local rc=$?
  if [ "$MUTATED" -eq 1 ] && [ -f "$BACKUP" ]; then
    say "Deployment failed (exit $rc); attempting rollback from $BACKUP"
    systemctl stop "$SERVICE" || true
    rm -rf "$APP_DIR"
    tar -xzf "$BACKUP" -C "$(dirname "$APP_DIR")" || say "CRITICAL: could not extract backup"
    systemctl restart "$SERVICE" || true
    if systemctl is-active --quiet "$SERVICE"; then
      say "ROLLBACK SUCCESS: previous version restored and service active."
    else
      say "CRITICAL: rollback attempted but service is not active; inspect journalctl -u $SERVICE."
    fi
  fi
  rm -rf "$TMP"
  exit "$rc"
}
trap rollback EXIT
say "Downloading and validating release archive"
curl --fail --silent --show-error --location --retry 3 "$URL" -o "$TMP/release.zip" || fail "Release asset download failed."
unzip -tq "$TMP/release.zip" || fail "ZIP integrity test failed."
unzip -q "$TMP/release.zip" -d "$TMP/unpacked"
# Support either a flat runtime ZIP or a single top-level directory.
SRC="$TMP/unpacked"
if [ ! -f "$SRC/run.py" ]; then
  mapfile -t CANDIDATES < <(find "$TMP/unpacked" -mindepth 2 -maxdepth 3 -type f -name run.py -printf '%h\n')
  [ "${#CANDIDATES[@]}" -eq 1 ] || fail "Archive does not contain one unambiguous run.py."
  SRC="${CANDIDATES[0]}"
fi
[ -f "$SRC/requirements.txt" ] || fail "Release archive has no requirements.txt."
say "Backing up current application, .env, and database"
tar -czf "$BACKUP" -C "$(dirname "$APP_DIR")" "$(basename "$APP_DIR")"
chmod 600 "$BACKUP"
say "Backup saved: $BACKUP"
# Release contents are copied over the live directory; secrets and persistent DB are explicitly excluded.
MUTATED=1
rsync -a --delete --exclude='/.env' --exclude='/bandit.db' --exclude='/.venv' --exclude='/logs/' --exclude='/backups/' --exclude='/VERSION.txt' "$SRC/" "$APP_DIR/"
# Confirm critical data survived untouched.
[ -f "$APP_DIR/.env" ] && [ -f "$APP_DIR/bandit.db" ] || fail "Safety check failed: .env/database missing."
[ -x "$VENV/bin/python" ] || fail "Existing runtime venv missing: $VENV"
say "Installing dependencies into existing virtual environment"
"$VENV/bin/python" -m pip install --disable-pip-version-check -r "$APP_DIR/requirements.txt"
say "Compiling Python sources"
"$VENV/bin/python" -m compileall -q "$APP_DIR" -x '/(.venv|__pycache__|\.git)/' || fail "Python compile check failed."
if [ -f "$APP_DIR/selftest.py" ]; then
  say "Running project self-test"
  (cd "$APP_DIR" && "$VENV/bin/python" selftest.py) || fail "Project self-test failed."
fi
say "Restarting service: $SERVICE"
systemctl restart "$SERVICE"
sleep 4
if systemctl is-active --quiet "$SERVICE"; then
  say "SUCCESS: deployed $TAG; service active."
  printf '%s\n' "$TAG" > "$APP_DIR/VERSION.txt"
  say "Version marker written to $APP_DIR/VERSION.txt"
  say "Deployment log: $LOG_FILE"
  MUTATED=0
  exit 0
fi
fail "Service failed to become active after restart"
