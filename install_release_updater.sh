#!/usr/bin/env bash
set -Eeuo pipefail
# Install a systemd timer that checks GitHub Releases every 15 minutes.
[ "$(id -u)" -eq 0 ] || { echo "Run as root: sudo bash install_release_updater.sh"; exit 1; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$ROOT/scripts/deploy_latest_release.sh"
[ -f "$SOURCE" ] || { echo "Missing $SOURCE"; exit 1; }
install -o root -g root -m 0750 "$SOURCE" /usr/local/sbin/bandit-city-deploy-latest
cat > /etc/systemd/system/bandit-city-release-update.service <<'UNIT'
[Unit]
Description=Check and deploy latest published Bandit City release
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
User=root
Environment=BANDIT_REPO=shelabin2017-ui/Bandit-City
Environment=BANDIT_APP_DIR=/root/Bandit-City
Environment=BANDIT_SERVICE=bandit-city.service
Environment=BANDIT_VENV=/root/Bandit-City/.venv
ExecStart=/usr/local/sbin/bandit-city-deploy-latest
TimeoutStartSec=15min
UNIT
cat > /etc/systemd/system/bandit-city-release-update.timer <<'UNIT'
[Unit]
Description=Poll GitHub for Bandit City releases

[Timer]
OnBootSec=5min
OnUnitActiveSec=15min
RandomizedDelaySec=90
Persistent=true
Unit=bandit-city-release-update.service

[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now bandit-city-release-update.timer
echo "Installed. Timer status:"
systemctl --no-pager --full status bandit-city-release-update.timer
echo "No bot restart is performed by this installer. First release deployment occurs on the next timer tick."
