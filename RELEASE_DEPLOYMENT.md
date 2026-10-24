# Bandit City versioned releases and VPS auto-deploy

## Release flow

1. Commit the intended release to `modernize-gameplay-2026-10` and verify CI.
2. Create and push a semantic version tag pointing at that commit, e.g. `v1.0.0`.
3. `.github/workflows/publish-release.yml` runs tests, builds `bandit-city-release.zip` without secrets/database/runtime folders, and publishes a GitHub Release.
4. The VPS updater polls the public Releases API every 15 minutes after its one-time installation. It deploys only a new tag and records the installed tag in `VERSION.txt`.

## One-time VPS installation

First publish a release. Then copy the repository's `install_release_updater.sh` and `scripts/deploy_latest_release.sh` to the server (or fetch the two files from the chosen branch), and run:

```bash
sudo bash install_release_updater.sh
```

The installer enables `bandit-city-release-update.timer`. Monitor it with:

```bash
systemctl list-timers bandit-city-release-update.timer
systemctl status bandit-city-release-update.service
journalctl -u bandit-city-release-update.service -n 100 --no-pager
ls -lt /var/log/bandit-city/deploy-*.log
ls -lt /var/backups/bandit-city/
```

To disable automatic deploys:

```bash
sudo systemctl disable --now bandit-city-release-update.timer
```

## Safety behavior

- Requires the existing application directory, `.env`, `bandit.db`, and runtime virtualenv; otherwise it refuses to deploy.
- Downloads only the release asset named `bandit-city-release.zip`, verifies ZIP integrity and checks for `run.py` and `requirements.txt`.
- Backs up the entire application directory before changing files.
- Excludes `.env`, `bandit.db`, `.venv`, logs, backups and version marker from rsync deletion/copy.
- Installs requirements into the existing virtualenv, compiles Python, runs `selftest.py` when present, then restarts and checks systemd.
- On a failure after files are changed, the EXIT trap restores the backup and attempts to restart the previous version.
- Backups are root-owned by default and set to mode 600.
- GitHub Actions are used to build releases; the VPS does not need a Git checkout or GitHub token for public releases.

## Important

A GitHub Release is not considered available until a `vX.Y.Z` tag has been pushed and the release workflow has completed successfully. The first release should be verified manually before enabling the timer on a production VPS. The updater does not run during this repository change and has not changed the live VPS.
