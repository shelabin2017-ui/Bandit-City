"""Safe runtime diagnostics for Bandit City.

Only repairs known, additive SQLite schema omissions. It never edits Python
source, deletes player data, or attempts to rewrite a corrupt database.
"""
import logging
import time
import json
import datetime

REQUIRED_TABLES = {
    "users", "settings", "businesses", "cars", "items", "city_events",
    "event_participation", "player_status", "mission_progress",
    "sms_messages", "phone_contacts", "npc_state", "npc_cooldowns",
}


def run_diagnostics(db):
    """Check SQLite integrity and core schema; repair missing tables additively."""
    try:
        with db.connect() as conn:
            check = str(conn.execute("PRAGMA quick_check").fetchone()[0])
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        if check.lower() != "ok":
            logging.critical("Auto-diagnostics: SQLite quick_check failed: %s", check)
            return {"ok": False, "repaired": False, "reason": "database_integrity", "detail": check}

        missing = sorted(REQUIRED_TABLES - tables)
        if missing:
            logging.warning("Auto-diagnostics: missing core tables: %s; trying safe schema repair", missing)
            # Database.init uses CREATE TABLE IF NOT EXISTS and additive column
            # migrations. It does not drop or recreate player tables.
            db.init()
            db.seed_promos()
            with db.connect() as conn:
                after = {
                    row[0] for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                check_after = str(conn.execute("PRAGMA quick_check").fetchone()[0])
            still_missing = sorted(REQUIRED_TABLES - after)
            if check_after.lower() != "ok" or still_missing:
                logging.error(
                    "Auto-diagnostics: schema repair incomplete; missing=%s integrity=%s",
                    still_missing, check_after,
                )
                return {
                    "ok": False, "repaired": True, "reason": "schema_repair_incomplete",
                    "missing": still_missing, "detail": check_after,
                }
            logging.warning("Auto-diagnostics: additive schema repair succeeded")
            return {"ok": True, "repaired": True, "missing_before": missing}

        return {"ok": True, "repaired": False, "tables": len(tables)}
    except Exception as exc:
        # Fail closed: never perform speculative repairs to unknown failures.
        logging.exception("Auto-diagnostics failed; automatic repair was not attempted")
        return {"ok": False, "repaired": False, "reason": "diagnostics_exception", "detail": str(exc)[:300]}


def _read_current_status(db):
    try:
        raw = db.get_setting("diagnostics_current_status", "{}")
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _write_current_status(db, result):
    checked_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    status = {
        "ok": bool(result.get("ok")),
        "checked_at": checked_at,
        "reason": "" if result.get("ok") else str(result.get("reason", "unknown")),
        "detail": "" if result.get("ok") else str(result.get("detail", result))[:300],
        "repaired": bool(result.get("repaired")),
    }
    # Keep only the CURRENT state. A successful check clears the active error report.
    db.set_setting("diagnostics_current_status", json.dumps(status, ensure_ascii=False))
    return status


def diagnostics_worker(db, interval_seconds=300):
    """Run checks; log transitions, and clear the current issue after a healthy check."""
    previous_ok = None
    while True:
        result = run_diagnostics(db)
        previous = _read_current_status(db)
        try:
            status = _write_current_status(db, result)
        except Exception:
            status = {"ok": bool(result.get("ok")), "reason": result.get("reason", "status_storage_failed")}
            logging.exception("Auto-diagnostics: could not update current status")
        if result.get("ok"):
            if previous_ok is False or previous.get("ok") is False:
                logging.info("Auto-diagnostics: RECOVERED; previous active error report cleared.")
            elif previous_ok is None:
                logging.info("Auto-diagnostics: OK (repaired=%s)", result.get("repaired", False))
            previous_ok = True
        else:
            if previous_ok is not False:
                logging.error("Auto-diagnostics: ATTENTION REQUIRED: %s", status)
            previous_ok = False
        time.sleep(max(30, int(interval_seconds)))
