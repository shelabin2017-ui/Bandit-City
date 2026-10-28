"""Persistent announcements and admin controls for timed city events."""
import datetime
import logging
import time

from catalog import EVENTS, active_events as catalog_active_events
from release import announce_release


def event_overrides(db):
    overrides = {}
    for code in EVENTS:
        value = str(db.get_setting("city_event:" + code, "") or "").strip().lower()
        if value in {"on", "off"}:
            overrides[code] = value
    return overrides


def active_events(db, now=None):
    return catalog_active_events(now=now, overrides=event_overrides(db))


def _utc_now(now=None):
    if now is None:
        return datetime.datetime.now(datetime.timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=datetime.timezone.utc)
    return now.astimezone(datetime.timezone.utc)


def _announcement(code, event, phase, now):
    date_label = now.strftime("%d.%m.%Y")
    hooks = [
        "Город не стоит на месте — самое время включиться.",
        "У тебя есть шанс забрать ограниченную награду, пока событие активно.",
        "Не откладывай: условия события доступны в меню города.",
        "Улица сегодня живёт этим событием. Проверь цели и участвуй.",
    ]
    hook = hooks[(now.timetuple().tm_yday + len(code)) % len(hooks)]
    lines = []
    if phase == "start":
        lines.extend(["🚨 В ГОРОДЕ СТАРТОВАЛО СОБЫТИЕ", str(event.get("title") or code), "", str(event.get("description") or "В городе началось новое событие.")])
    elif phase == "manual":
        lines.extend(["📣 СОБЫТИЕ ГОРОДА • АКТИВНО СЕЙЧАС", str(event.get("title") or code), "", str(event.get("description") or "В городе проходит ограниченное событие.")])
    else:
        lines.extend(["🌆 СЕГОДНЯ В BANDIT CITY", str(event.get("title") or code), "", "Событие всё ещё активно. " + hook])
    goal = event.get("goal_label")
    if goal:
        lines.extend(["", "🎯 ЦЕЛЬ: " + str(goal)])
    end_at = event.get("end_at")
    if end_at:
        try:
            end = datetime.datetime.fromisoformat(str(end_at).replace("Z", "+00:00"))
            lines.extend(["", "⏳ Завершение: " + end.strftime("%d.%m.%Y %H:%M UTC")])
        except ValueError:
            pass
    lines.extend(["", hook, "🎁 Открой «🌆 События города», чтобы посмотреть условия и награды."])
    return "\n".join(lines)


def announce_active_events(db, vk, group_id, now=None, delay_seconds=0.35):
    """Announce event starts and daily live status; each broadcast is idempotent."""
    now = _utc_now(now)
    active = active_events(db, now)
    results = {}
    date_key = now.strftime("%Y-%m-%d")
    for code, event in active.items():
        start_at = str(event.get("start_at") or "legacy")
        start_id = "city-event-start:{}:{}".format(code, start_at)
        try:
            results[code] = announce_release(
                db, vk, group_id, start_id, _announcement(code, event, "start", now),
                delay_seconds=delay_seconds,
            )
            # Daily reminders are distinct and use varied copy, not the same stale text.
            start_date = start_at[:10] if start_at != "legacy" else ""
            if start_date != date_key:
                daily_id = "city-event-live:{}:{}".format(code, date_key)
                results[code + ":daily"] = announce_release(
                    db, vk, group_id, daily_id, _announcement(code, event, "daily", now),
                    delay_seconds=delay_seconds,
                )
        except Exception:
            logging.exception("Event announcement failed: event=%s", code)

    # Admin can request an immediate announcement using /event announce CODE.
    for code, event in EVENTS.items():
        if str(db.get_setting("city_event_announce:" + code, "") or "") != "1":
            continue
        if code not in active:
            logging.info("Manual event announcement skipped: %s is not active", code)
            db.set_setting("city_event_announce:" + code, "0")
            continue
        force_id = "city-event-manual:{}:{}".format(code, int(time.time()))
        try:
            results[code + ":manual"] = announce_release(
                db, vk, group_id, force_id, _announcement(code, event, "manual", now),
                delay_seconds=delay_seconds,
            )
        except Exception:
            logging.exception("Manual event announcement failed: event=%s", code)
        finally:
            db.set_setting("city_event_announce:" + code, "0")
    return results


def event_announcer_worker(db, vk, group_id, interval_seconds=60, admin_ids=None):
    """Check schedules, broadcast starts, and privately notify admins once per event."""
    admin_ids = {int(uid) for uid in (admin_ids or set())}
    while True:
        now = _utc_now()
        results = announce_active_events(db, vk, group_id, now=now)
        for code, event in active_events(db, now).items():
            notice_base = "city_event_admin_notified:{}:{}".format(code, str(event.get("start_at") or "legacy"))
            message = "🔔 BANDIT CITY • УВЕДОМЛЕНИЕ АДМИНУ\n\nСобытие активно: {}\nКод: {}\nПроверь рассылку и игровую механику.".format(event.get("title") or code, code)
            for admin_id in admin_ids:
                notice_key = notice_base + ":" + str(admin_id)
                if str(db.get_setting(notice_key, "0")) == "1":
                    continue
                try:
                    vk.messages.send(user_id=admin_id, random_id=int(time.time() * 1000) % 2147483647, message=message)
                    db.set_setting(notice_key, "1")
                except Exception:
                    logging.exception("Could not privately notify admin about city event: %s uid=%s", code, admin_id)
        time.sleep(max(15, int(interval_seconds)))
