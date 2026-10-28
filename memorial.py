"""Persistent one-time memorial announcement for Bandit City."""
import logging
import time
from datetime import datetime, time as wall_time
from zoneinfo import ZoneInfo

from release import announce_release


MEMORIAL_RELEASE_ID = "memorial-stas-2026-10-28"
MEMORIAL_MESSAGE = """🕯 МИНУТА МОЛЧАНИЯ — В ПАМЯТЬ О СТАСЕ

Сегодня официально подтверждена гибель Стаса, родившегося 23 февраля 2003 года. С 18 октября он числился без вести пропавшим.

BANDIT CITY выражает искренние соболезнования родным, близким и всем, кто знал Стаса.

Просим каждого игрока остановиться хотя бы на минуту и почтить его память молчанием.

Светлая память, Стас. Помним. Скорбим."""

MEMORIAL_TIMEZONE = ZoneInfo("Europe/Moscow")
MEMORIAL_DATE = "2026-10-28"
MEMORIAL_HOUR = 21
MEMORIAL_MINUTE = 33


def announce_memorial(db, vk, group_id):
    """Send a persistent, resumable memorial announcement to eligible players."""
    try:
        result = announce_release(
            db,
            vk,
            group_id,
            MEMORIAL_RELEASE_ID,
            MEMORIAL_MESSAGE,
        )
        logging.info("Stas memorial announcement finished: %s", result)
        return result
    except Exception:
        logging.exception("Failed to send Stas memorial announcement")
        return None


def scheduled_memorial_worker(db, vk, group_id):
    """Wait for 21:33 Moscow time on 2026-10-28, then send the memorial once."""
    target_date = datetime.strptime(MEMORIAL_DATE, "%Y-%m-%d").date()
    while True:
        now = datetime.now(MEMORIAL_TIMEZONE)
        if now.date() > target_date:
            logging.error("Stas memorial schedule expired; not sending late automatically")
            return
        if now.date() == target_date and (now.hour, now.minute) >= (MEMORIAL_HOUR, MEMORIAL_MINUTE):
            break
        target = datetime.combine(target_date, wall_time(MEMORIAL_HOUR, MEMORIAL_MINUTE), tzinfo=MEMORIAL_TIMEZONE)
        remaining = max(1, min(30, int((target - now).total_seconds())))
        time.sleep(remaining)
    logging.info("Scheduled Stas memorial broadcast starting at %s", datetime.now(MEMORIAL_TIMEZONE).isoformat())
    announce_memorial(db, vk, group_id)
