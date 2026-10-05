"""Bandit City V5 compatibility layer."""
from . import bridge

if hasattr(bridge, "EVENT_CLOTHING"):
    bridge.CLOTHING = {**bridge.CLOTHING, **bridge.EVENT_CLOTHING}

# Keep secret/event promo rewards in the same event collection used by the UI.
try:
    from db import Database
    _original_seed_promos = Database.seed_promos
    _original_redeem_promo = Database.redeem_promo
    _event_names = {name for rows in bridge.EVENT_CLOTHING.values() for name, _, _ in rows}
    _extra_promos = [
        ("FOUNDER-2026", "Founder Event Drop", 350000, 700, "🧥 Founder Jacket", "clothes", 0),
        ("NEON-2026", "Neon City Event Drop", 400000, 800, "🌃 Neon City Background", "background", 0),
        ("BLACKOUT-2026", "Blackout Event Drop", 600000, 1000, "⛓ Blackout Chain", "accessory", 0),
        ("ANNIVERSARY-2026", "Anniversary Event Drop", 1000000, 1500, "🏆 Bandit Legend Outfit", "clothes", 0),
        ("NIGHTFALL-X", "Nightfall Secret Drop", 300000, 600, "🎭 Nightfall Mask", "head", 0),
        ("PRIME-2026", "Prime Secret Drop", 750000, 1200, "👑 Prime Hair", "hair", 0),
        ("GOLDEN-2026", "Golden Bullet Secret Drop", 1250000, 1800, "🔫 Golden Bullet", "accessory", 0),
    ]

    def _seed_promos_with_events(self):
        _original_seed_promos(self)
        with self.connect() as c:
            for promo in _extra_promos:
                c.execute(
                    "INSERT OR IGNORE INTO promo_codes(code,title,reward_cash,reward_xp,reward_item,reward_slot,max_uses) VALUES(?,?,?,?,?,?,?)",
                    promo,
                )

    def _redeem_promo_with_event_collection(self, user_id, code):
        ok, message = _original_redeem_promo(self, user_id, code)
        if ok:
            with self.connect() as c:
                promo = c.execute("SELECT reward_item,reward_slot FROM promo_codes WHERE code=?", (code.strip().upper(),)).fetchone()
                if promo and promo["reward_item"] in _event_names:
                    c.execute(
                        "INSERT OR IGNORE INTO v5_wardrobe(user_id,category,name,price,bought_at) VALUES(?,?,?,?,strftime('%s','now'))",
                        (user_id, "🎪 Ивент • Эксклюзивы", promo["reward_item"], 0),
                    )
                    if promo["reward_slot"] == "background":
                        c.execute("UPDATE user_appearance SET background=?,updated_at=strftime('%s','now') WHERE user_id=?", (promo["reward_item"], user_id))
        return ok, message

    Database.seed_promos = _seed_promos_with_events
    Database.redeem_promo = _redeem_promo_with_event_collection
except Exception:
    pass
