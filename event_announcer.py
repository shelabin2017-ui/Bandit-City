"""Persistent announcements for timed catalogue events."""
import logging
import time

from catalog import active_events
from release import announce_release


def announce_active_events(db, vk, group_id, now=None, delay_seconds=0.35):
    """Announce each timed event once, with per-player delivery state in SQLite."""
    active = active_events(now)
    results = {}
    for code, event in active.items():
        start_at = str(event.get("start_at") or "legacy")
        release_id = "event-start:{}:{}".format(code, start_at)
        lines = [
            str(event.get("title") or "🌆 СОБЫТИЕ ГОРОДА"),
            "",
            str(event.get("description") or "В городе началось новое событие."),
        ]
        goal = event.get("goal_label")
        if goal:
            lines.extend(["", "🎯 ЗАДАНИЕ СОБЫТИЯ: " + str(goal)])
        lines.extend(["", "🎁 Загляни в «🌆 События города», чтобы узнать условия и забрать доступные награды."])
        try:
            results[code] = announce_release(
                db, vk, group_id, release_id, "\n".join(lines),
                delay_seconds=delay_seconds,
            )
        except Exception:
            # Keep the worker alive; the next pass retries unfinished deliveries.
            logging.exception("Event announcement failed: event=%s", code)
    return results


def event_announcer_worker(db, vk, group_id, interval_seconds=60):
    """Check event start windows once per minute; state survives bot restarts."""
    while True:
        announce_active_events(db, vk, group_id)
        time.sleep(max(15, int(interval_seconds)))
