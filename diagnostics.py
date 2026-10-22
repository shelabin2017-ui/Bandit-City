"""Safe runtime diagnostics for Bandit City.

Only repairs known, additive SQLite schema omissions. It never edits Python
source, deletes player data, or attempts to rewrite a corrupt database.
"""
import logging
import time

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


def diagnostics_worker(db, interval_seconds=300):
    """Run checks immediately, then every five minutes by default."""
    while True:
        result = run_diagnostics(db)
        if result.get("ok"):
            logging.info("Auto-diagnostics: OK (repaired=%s)", result.get("repaired", False))
        else:
            logging.error("Auto-diagnostics: ATTENTION REQUIRED: %s", result)
        time.sleep(max(30, int(interval_seconds)))
