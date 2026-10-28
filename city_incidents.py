"""Interactive, repeat-limited city incidents tied to the daily news feed."""
import datetime
import hashlib

from city_news import daypart_label

INCIDENTS = {
    "morning": [
        {"code": "rescue_cat", "title": "🐈 Спасти кошку", "story": "Кошка застряла на крыше жилого дома. Жители ищут добровольца.", "action": "🤝 Помочь городу", "success": "🐈 Кошка спасена! Хозяева передали благодарность.", "cash": 1800, "xp": 3},
        {"code": "lost_bag", "title": "🧳 Найти владельца сумки", "story": "На остановке нашли сумку с личными вещами. Помоги передать её в бюро находок.", "action": "🤝 Помочь городу", "success": "🧳 Сумка передана владельцу через бюро находок.", "cash": 1500, "xp": 3},
        {"code": "lost_dog", "title": "🐕 Найти пропавшего пса", "story": "Во дворах ищут рыжего пса по кличке Рокки. Соседи прочёсывают район.", "action": "🤝 Помочь городу", "success": "🐕 Рокки нашёлся! Хозяин отблагодарил тебя.", "cash": 2000, "xp": 4},
    ],
    "day": [
        {"code": "accident_help", "title": "🚑 Помочь после ДТП", "story": "На перекрёстке произошло ДТП. Экстренным службам нужна помощь с организацией движения.", "action": "🤝 Помочь городу", "success": "🚑 Ты помог организовать движение до приезда служб.", "cash": 2200, "xp": 4},
        {"code": "found_backpack", "title": "🎒 Вернуть находку", "story": "В парке нашли забытый рюкзак. Владелец оставил описание в городском чате.", "action": "🤝 Помочь городу", "success": "🎒 Рюкзак вернулся к владельцу.", "cash": 1600, "xp": 3},
        {"code": "warehouse_help", "title": "📦 Помочь складу", "story": "На городском складе не хватает рук для срочной разгрузки поставки.", "action": "🤝 Помочь городу", "success": "📦 Поставка разгружена вовремя.", "cash": 2400, "xp": 4},
    ],
    "evening": [
        {"code": "street_concert", "title": "🎤 Помочь музыкантам", "story": "Уличные музыканты готовят выступление, но им нужна помощь с оборудованием.", "action": "🤝 Помочь городу", "success": "🎤 Концерт состоялся, площадь наполнилась музыкой.", "cash": 1900, "xp": 3},
        {"code": "garage_help", "title": "🔧 Помочь мастерской", "story": "В мастерской сломался подъёмник, а несколько заказов нужно закончить до закрытия.", "action": "🤝 Помочь городу", "success": "🔧 Заказы завершены, механики благодарят за помощь.", "cash": 2500, "xp": 4},
        {"code": "street_lights", "title": "💡 Включить огни набережной", "story": "На набережной не работает часть подсветки. Рабочие ищут помощника.", "action": "🤝 Помочь городу", "success": "💡 Подсветка восстановлена — набережная снова сияет.", "cash": 1800, "xp": 3},
    ],
    "night": [
        {"code": "power_outage", "title": "🔦 Помочь при отключении света", "story": "В одном из кварталов пропало электричество. Аварийная бригада ищет безопасную помощь.", "action": "🤝 Помочь городу", "success": "🔦 Ты помог предупредить жителей, пока бригада восстанавливала питание.", "cash": 2300, "xp": 4},
        {"code": "night_cat", "title": "🐈 Снять кошку с крыши", "story": "Ночью жители услышали мяуканье на крыше старого дома. Нужна помощь.", "action": "🤝 Помочь городу", "success": "🐈 Кошка благополучно спущена с крыши.", "cash": 2100, "xp": 4},
        {"code": "fog_warning", "title": "🌫️ Предупредить водителей", "story": "Набережную накрыл туман. Городской диспетчер просит предупредить водителей.", "action": "🤝 Помочь городу", "success": "🌫️ Водители получили предупреждение, риск аварий снизился.", "cash": 1700, "xp": 3},
    ],
}


def incident_period(now=None):
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)
    now = now.astimezone(datetime.timezone.utc)
    part = "morning" if 5 <= now.hour < 12 else "day" if 12 <= now.hour < 17 else "evening" if 17 <= now.hour < 22 else "night"
    return now, part


def active_incident(now=None):
    now, part = incident_period(now)
    pool = INCIDENTS[part]
    seed = "{}:{}".format(now.date().isoformat(), part)
    offset = int.from_bytes(hashlib.sha256(seed.encode("utf-8")).digest()[:4], "big") % len(pool)
    incident = dict(pool[offset])
    incident["period"] = part
    incident["period_label"] = daypart_label(now.hour)
    incident["period_key"] = now.strftime("%Y-%m-%d") + ":" + part
    return incident
