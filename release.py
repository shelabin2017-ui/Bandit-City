"""Persistent, idempotent broadcast for newly deployed Bandit City releases."""
import logging
import random
import time
from pathlib import Path


DEFAULT_ANNOUNCEMENT = (
    "Вышло обновление игры! Мы продолжаем исправлять ошибки и улучшать игровые механики. "
    "Заходи в город и проверяй изменения."
)


def _ensure_schema(db):
    with db.connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS release_broadcasts (
                release_id TEXT PRIMARY KEY,
                message TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                completed_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS release_broadcast_recipients (
                release_id TEXT NOT NULL,
                vk_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                random_id INTEGER NOT NULL,
                last_error TEXT,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (release_id, vk_id),
                FOREIGN KEY (release_id) REFERENCES release_broadcasts(release_id)
            );
        """)


def announce_release(db, vk, group_id, release_id, message, delay_seconds=0.35, sleeper=time.sleep):
    """Send one release announcement per eligible player, resuming after interruptions."""
    release_id = str(release_id or "").strip()
    message = str(message or "").strip()
    if not release_id or not message:
        logging.warning("Release announcement skipped: release ID or message is empty")
        return {"sent": 0, "skipped": 0, "failed": 0, "total": 0, "already_done": True}

    _ensure_schema(db)
    now = int(time.time())
    with db.connect() as conn:
        existing = conn.execute(
            "SELECT message, completed_at FROM release_broadcasts WHERE release_id=?",
            (release_id,),
        ).fetchone()
        if existing and existing["completed_at"] is not None:
            logging.info("Release announcement already completed: %s", release_id)
            return {"sent": 0, "skipped": 0, "failed": 0, "total": 0, "already_done": True}
        if not existing:
            conn.execute(
                "INSERT INTO release_broadcasts(release_id,message,created_at,completed_at) VALUES(?,?,?,NULL)",
                (release_id, message, now),
            )
            targets = conn.execute(
                "SELECT vk_id FROM users WHERE banned=0 ORDER BY id"
            ).fetchall()
            for row in targets:
                conn.execute(
                    """INSERT OR IGNORE INTO release_broadcast_recipients
                       (release_id,vk_id,status,attempts,random_id,last_error,updated_at)
                       VALUES(?,?,'pending',0,?,NULL,?)""",
                    (release_id, int(row["vk_id"]), random.randint(1, 2_147_483_647), now),
                )
        stored = conn.execute(
            "SELECT message FROM release_broadcasts WHERE release_id=?", (release_id,)
        ).fetchone()
        message = str(stored["message"])
        pending = conn.execute(
            """SELECT vk_id,attempts,random_id FROM release_broadcast_recipients
               WHERE release_id=? AND (status='pending' OR (status='failed' AND attempts<3))
               ORDER BY vk_id""",
            (release_id,),
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) n FROM release_broadcast_recipients WHERE release_id=?",
            (release_id,),
        ).fetchone()["n"]

    sent = skipped = failed = 0
    for row in pending:
        target = int(row["vk_id"])
        try:
            try:
                permission = vk.messages.isMessagesFromGroupAllowed(
                    group_id=int(group_id), user_id=target
                )
                if not bool(permission.get("is_allowed", 0)):
                    with db.connect() as conn:
                        conn.execute(
                            """UPDATE release_broadcast_recipients
                               SET status='skipped',last_error=?,updated_at=?
                               WHERE release_id=? AND vk_id=?""",
                            ("Messages from group are not allowed", int(time.time()), release_id, target),
                        )
                    skipped += 1
                    continue
            except Exception as exc:
                # Some API wrappers/permissions may not support the permission check.
                logging.warning("Release permission check failed for %s; trying send: %s", target, exc)

            vk.messages.send(
                user_id=target,
                random_id=int(row["random_id"]),
                message="📢 BANDIT CITY\n\n" + message,
            )
            with db.connect() as conn:
                conn.execute(
                    """UPDATE release_broadcast_recipients
                       SET status='sent',last_error=NULL,updated_at=?
                       WHERE release_id=? AND vk_id=?""",
                    (int(time.time()), release_id, target),
                )
            sent += 1
            logging.info("Release announcement sent: release=%s target=%s", release_id, target)
            if delay_seconds > 0:
                sleeper(delay_seconds)
        except Exception as exc:
            attempts = int(row["attempts"]) + 1
            with db.connect() as conn:
                conn.execute(
                    """UPDATE release_broadcast_recipients
                       SET status='failed',attempts=?,last_error=?,updated_at=?
                       WHERE release_id=? AND vk_id=?""",
                    (attempts, str(exc)[:500], int(time.time()), release_id, target),
                )
            failed += 1
            logging.exception("Release announcement failed: release=%s target=%s", release_id, target)

    with db.connect() as conn:
        unfinished = conn.execute(
            """SELECT COUNT(*) n FROM release_broadcast_recipients
               WHERE release_id=? AND (status='pending' OR (status='failed' AND attempts<3))""",
            (release_id,),
        ).fetchone()["n"]
        if unfinished == 0:
            conn.execute(
                "UPDATE release_broadcasts SET completed_at=? WHERE release_id=?",
                (int(time.time()), release_id),
            )
        statuses = {
            row["status"]: row["n"]
            for row in conn.execute(
                """SELECT status,COUNT(*) n FROM release_broadcast_recipients
                   WHERE release_id=? GROUP BY status""",
                (release_id,),
            ).fetchall()
        }

    summary = {
        "sent": int(statuses.get("sent", 0)),
        "skipped": int(statuses.get("skipped", 0)),
        "failed": int(statuses.get("failed", 0)),
        "total": int(total),
        "already_done": False,
    }
    logging.info("Release broadcast summary: release=%s %s", release_id, summary)
    return summary


def announce_new_release(db, vk, group_id, release_file=None, delay_seconds=0.35):
    """Read RELEASE.txt and announce its build once per database."""
    path = Path(release_file) if release_file else Path(__file__).resolve().with_name("RELEASE.txt")
    if not path.exists():
        logging.warning("Release announcement skipped: %s not found", path)
        return None

    build = ""
    announcement = DEFAULT_ANNOUNCEMENT
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Build:"):
            build = line.split(":", 1)[1].strip()
        elif line.startswith("Announcement:"):
            announcement = line.split(":", 1)[1].strip() or DEFAULT_ANNOUNCEMENT

    if not build:
        logging.warning("Release announcement skipped: RELEASE.txt has no Build field")
        return None
    return announce_release(db, vk, group_id, build, announcement, delay_seconds=delay_seconds)
