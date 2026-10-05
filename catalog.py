"""Bandit City content catalog.

Static content only: no secrets, tokens or player data.
Normal catalogue entries are public. Event/promo entries are intentionally
hidden from normal catalogue screens and can be granted only by event/promo
systems.
"""

CARS = [
    {"id":"sentinel","name":"Sentinel","category":"sedan","speed":110,"price":180000},
    {"id":"buffalo","name":"Buffalo","category":"sport","speed":145,"price":420000},
    {"id":"elegy","name":"Elegy","category":"sport","speed":155,"price":650000},
    {"id":"sultan","name":"Sultan","category":"sport","speed":165,"price":850000},
    {"id":"infernus","name":"Infernus","category":"super","speed":205,"price":2200000},
    {"id":"bullet","name":"Bullet","category":"super","speed":215,"price":3000000},
    {"id":"turismo","name":"Turismo","category":"super","speed":225,"price":4200000},
    {"id":"comet","name":"Comet","category":"sport","speed":185,"price":1700000},
    {"id":"banshee","name":"Banshee","category":"sport","speed":195,"price":1950000},
    {"id":"huntley","name":"Huntley","category":"suv","speed":125,"price":520000},
    {"id":"sandking","name":"Sandking","category":"offroad","speed":120,"price":480000},
    {"id":"bf400","name":"BF-400","category":"bike","speed":175,"price":700000},
]

ITEMS = [
    {"id":"phone","name":"📱 Телефон","price":15000},
    {"id":"lockpick","name":"🔧 Отмычка","price":12000},
    {"id":"medkit","name":"🩹 Аптечка","price":18000},
    {"id":"energy","name":"⚡ Энергетик","price":9000},
    {"id":"mask","name":"🎭 Маска","price":25000},
    {"id":"armor","name":"🛡 Бронежилет","price":85000},
    {"id":"toolkit","name":"🧰 Набор механика","price":55000},
    {"id":"vip_pass","name":"🎫 VIP-пропуск","price":250000},
    {"id":"lucky_chip","name":"🪙 Счастливая фишка","price":75000},
    {"id":"gift_box","name":"🎁 Подарочная коробка","price":50000},
]

CLOTHES = [
    {"id":"street_black","name":"🖤 Street Black","slot":"clothes","price":45000},
    {"id":"street_white","name":"🤍 Street White","slot":"clothes","price":45000},
    {"id":"gangster","name":"🕶 Gangster Suit","slot":"clothes","price":180000},
    {"id":"racer","name":"🏁 Racer Jacket","slot":"clothes","price":125000},
    {"id":"los_santos","name":"🌴 Los Santos Hoodie","slot":"clothes","price":90000},
    {"id":"urban","name":"🏙 Urban Set","slot":"clothes","price":110000},
    {"id":"combat","name":"🪖 Combat Set","slot":"clothes","price":240000},
]

ACCESSORIES = [
    {"id":"gold_chain","name":"⛓ Золотая цепь","slot":"accessory","price":150000},
    {"id":"silver_chain","name":"🔗 Серебряная цепь","slot":"accessory","price":80000},
    {"id":"black_glasses","name":"🕶 Black Shades","slot":"accessory","price":65000},
    {"id":"red_glasses","name":"😎 Red Shades","slot":"accessory","price":70000},
    {"id":"cap","name":"🧢 City Cap","slot":"head","price":35000},
    {"id":"beanie","name":"🎩 Night Beanie","slot":"head","price":30000},
]

WEAPONS = [
    {"id":"bat","name":"🏏 Бита","price":35000},
    {"id":"knife","name":"🔪 Нож","price":60000},
    {"id":"pistol","name":"🔫 Пистолет","price":180000},
    {"id":"smg","name":"🔫 SMG","price":420000},
]

PREMIUM = [
    {"id":"premium_tag","name":"💎 Premium Tag","price":350000},
    {"id":"premium_profile","name":"✨ Premium Profile","price":500000},
    {"id":"premium_case","name":"💎 Premium Case","price":750000},
]

EVENT_EXCLUSIVES = [
    {"id":"founder_jacket","name":"🖤 Founder Jacket","slot":"clothes","event":"founder","promo_only":True},
    {"id":"nightfall_mask","name":"🌑 Nightfall Mask","slot":"accessory","event":"nightfall","promo_only":True},
    {"id":"prime_hair","name":"👑 Prime Hair","slot":"hair","event":"prime","promo_only":True},
    {"id":"neon_background","name":"🌌 Neon City Background","slot":"background","event":"neon","promo_only":True},
    {"id":"blackout_chain","name":"⛓ Blackout Chain","slot":"accessory","event":"blackout","promo_only":True},
    {"id":"bandit_legend","name":"🏆 Bandit Legend Outfit","slot":"clothes","event":"anniversary","promo_only":True},
    {"id":"golden_bullet","name":"🚘 Golden Bullet","slot":"car","event":"anniversary","promo_only":True},
]

EVENTS = {
    "founder": {"title":"👑 FOUNDER DROP", "description":"Первый закрытый дроп Bandit City.", "drops": ["founder_jacket"], "start_at":"2026-10-01T00:00:00Z", "end_at":"2026-10-15T00:00:00Z"},
    "nightfall": {"title":"🌑 NIGHTFALL", "description":"Ночная серия эксклюзивов.", "drops": ["nightfall_mask"], "start_at":"2026-10-20T00:00:00Z", "end_at":"2026-11-03T00:00:00Z"},
    "prime": {"title":"💎 BANDIT PRIME", "description":"Премиальный закрытый сезон.", "drops": ["prime_hair"], "start_at":"2026-11-10T00:00:00Z", "end_at":"2026-11-24T00:00:00Z"},
    "neon": {"title":"🌌 NEON CITY", "description":"Временный неоновый ивент.", "drops": ["neon_background"], "start_at":"2026-12-01T00:00:00Z", "end_at":"2027-01-01T00:00:00Z"},
    "blackout": {"title":"🖤 BLACKOUT", "description":"Секретный лимитированный дроп.", "drops": ["blackout_chain"], "start_at":"2027-01-05T00:00:00Z", "end_at":"2027-01-12T00:00:00Z"},
    "anniversary": {"title":"🎉 BANDIT CITY ANNIVERSARY", "description":"Редкие награды за годовщину проекта.", "drops": ["bandit_legend", "golden_bullet"], "start_at":"2027-02-01T00:00:00Z", "end_at":"2027-02-15T00:00:00Z"},
}


def public_catalog():
    return {"cars":list(CARS),"items":list(ITEMS),"clothes":list(CLOTHES),"accessories":list(ACCESSORIES),"weapons":list(WEAPONS),"premium":list(PREMIUM)}


def _event_is_active(event, now=None):
    """Return True when an event is inside its optional time window.
    Missing boundaries mean no time restriction, which keeps legacy events active
    until an admin assigns a window.
    """
    import datetime as _dt
    if now is None:
        now = _dt.datetime.now(_dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=_dt.timezone.utc)
    start = event.get("start_at")
    end = event.get("end_at")
    if start:
        start = _dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
        if now < start:
            return False
    if end:
        end = _dt.datetime.fromisoformat(end.replace("Z", "+00:00"))
        if now >= end:
            return False
    return True


def active_events(now=None):
    return {
        key: event for key, event in EVENTS.items()
        if _event_is_active(event, now)
    }


def event_catalog(event_key, active_only=False, now=None):
    if active_only and event_key not in active_events(now):
        return []
    return [x for x in EVENT_EXCLUSIVES if x["event"] == event_key]


def find_event_item(item_id):
    for item in EVENT_EXCLUSIVES:
        if item["id"] == item_id:
            return item
    return None
