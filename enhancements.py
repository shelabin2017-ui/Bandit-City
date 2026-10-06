"""Bandit City gameplay extensions.

Loaded by run.py so the original bot stays backwards-compatible while gaining:
- multiple business types + upgrades;
- player targeting by VK ID, VK profile URL, nickname or referral link;
- referral/deep links shown to players;
- transfers, attacks and phone contacts accepting those links.
"""

import re
import time
from urllib.parse import parse_qs, urlparse


BUSINESSES = {
    "airport": {"name": "🏭 Контрабандистский аэропорт", "short": "Аэропорт", "price": 100_000_000, "income": 80_000, "refill": 40_000, "capacity": 5_000_000, "desc": "Большой стабильный поток нелегальных грузов."},
    "garage": {"name": "🔧 Автомастерская", "short": "Автомастерская", "price": 60_000_000, "income": 55_000, "refill": 30_000, "capacity": 4_000_000, "desc": "Ремонт, тюнинг и серые заказы."},
    "nightclub": {"name": "🪩 Ночной клуб", "short": "Ночной клуб", "price": 150_000_000, "income": 120_000, "refill": 65_000, "capacity": 6_000_000, "desc": "VIP-вечеринки, охрана и нелегальные сделки."},
    "casino": {"name": "🎰 Подпольное казино", "short": "Подпольное казино", "price": 300_000_000, "income": 220_000, "refill": 110_000, "capacity": 8_000_000, "desc": "Высокий доход и высокий риск."},
    "warehouse": {"name": "📦 Складской терминал", "short": "Склад", "price": 45_000_000, "income": 35_000, "refill": 22_000, "capacity": 7_000_000, "desc": "Логистика и хранение дефицитного товара."},
    "carwash": {"name": "🚿 Премиум-мойка", "short": "Премиум-мойка", "price": 35_000_000, "income": 28_000, "refill": 18_000, "capacity": 3_000_000, "desc": "Легальный фасад для грязных денег."},
    "security": {"name": "🛡 Охранное агентство", "short": "Охранное агентство", "price": 85_000_000, "income": 70_000, "refill": 35_000, "capacity": 5_000_000, "desc": "Охрана бизнеса, VIP и опасных клиентов."},
    "tech": {"name": "💻 Хакерский центр", "short": "Хакерский центр", "price": 200_000_000, "income": 165_000, "refill": 85_000, "capacity": 6_000_000, "desc": "Цифровые схемы, данные и дорогие заказы."},
}


def _money(value):
    return f"${int(value):,}".replace(",", " ")


def _parse_ref(value):
    text = str(value or "").strip()
    if "ref=" not in text.lower():
        return None
    try:
        parsed = urlparse(text if "://" in text else "https://" + text)
        query = parse_qs(parsed.query)
        for key in ("ref", "start", "startapp"):
            if query.get(key):
                return query[key][0].strip()
    except Exception:
        pass
    match = re.search(r"(?:^|[?&])ref=([^&#\s]+)", text, re.I)
    return match.group(1).strip() if match else None


def _vk_profile_from_value(self, value):
    """Resolve a VK profile URL/screen name through the bot's VK API."""
    text = str(value or "").strip()
    raw = text
    if raw.startswith("@"):
        raw = raw[1:].strip()

    if "://" in raw:
        try:
            parsed = urlparse(raw)
            host = (parsed.netloc or "").lower()
            if host not in {"vk.com", "www.vk.com", "vk.ru", "www.vk.ru"}:
                return None
            raw = parsed.path.strip("/")
        except Exception:
            return None
    elif raw.lower().startswith(("vk.com/", "vk.ru/")):
        raw = raw.split("/", 1)[1].strip("/")

    raw = raw.split("?", 1)[0].split("#", 1)[0].strip("/")
    if not raw or re.fullmatch(r"id\d+", raw, re.I) or raw.isdigit():
        return None

    api = getattr(self, "_vk_api", None)
    if api is None:
        return None

    try:
        rows = api.users.get(user_ids=[raw])
        if rows:
            return rows[0]
    except Exception:
        return None
    return None


def resolve_player(self, value):
    text = str(value or "").strip()
    if not text:
        return None

    ref = _parse_ref(text)
    with self.connect() as c:
        if ref:
            row = c.execute("SELECT * FROM users WHERE ref_code=?", (ref,)).fetchone()
            if row:
                return row

        raw = text
        if raw.startswith("@"):
            raw = raw[1:]
        if raw.lower().startswith("vk.com/") or raw.lower().startswith("vk.ru/"):
            raw = raw.split("/", 1)[1].split("?", 1)[0].split("#", 1)[0]
        match = re.fullmatch(r"id(\d+)", raw, re.I) or re.fullmatch(r"(\d+)", raw)
        if match:
            row = c.execute("SELECT * FROM users WHERE vk_id=?", (int(match.group(1)),)).fetchone()
            if row:
                return row

        row = c.execute("SELECT * FROM users WHERE ref_code=?", (text,)).fetchone()
        if row:
            return row
        row = c.execute("SELECT * FROM users WHERE lower(nickname)=lower(?)", (text,)).fetchone()
        if row:
            return row

    # The VK profile may be valid even when the player has never opened
    # Bandit City before. Resolve the public profile through VK API and
    # create the local player row only when a game action needs it.
    profile = _vk_profile_from_value(self, text)
    if profile:
        return self.get_or_create_user(int(profile["id"]))
    return None


def resolve_vk_id(self, value):
    row = resolve_player(self, value)
    return int(row["vk_id"]) if row else None


def _business_spec(b):
    return BUSINESSES.get(str(b["type"]), BUSINESSES["airport"])


def _income(spec, level):
    return int(spec["income"] * (1 + 0.25 * max(0, int(level) - 1)))


def _capacity(spec, level):
    return int(spec["capacity"] * (1 + 0.20 * max(0, int(level) - 1)))


def tick_business(self, c, b):
    now = int(time.time())
    minutes = max(0, (now - int(b["last_tick"])) // 60)
    if minutes <= 0:
        return 0
    spec = _business_spec(b)
    use = min(minutes, int(b["stock"]))
    income = use * _income(spec, b["level"])
    c.execute(
        "UPDATE businesses SET stock=stock-?,balance=balance+?,last_tick=? WHERE id=?",
        (use, income, now, b["id"]),
    )
    if not use:
        c.execute("UPDATE businesses SET last_tick=? WHERE id=?", (now, b["id"]))
    return income


def tick_all_businesses(self):
    with self.connect() as c:
        for b in c.execute("SELECT * FROM businesses").fetchall():
            tick_business(self, c, b)


def business(self, user_id):
    with self.connect() as c:
        b = c.execute("SELECT * FROM businesses WHERE user_id=?", (int(user_id),)).fetchone()
        if not b:
            return None
        tick_business(self, c, b)
        return c.execute("SELECT * FROM businesses WHERE user_id=?", (int(user_id),)).fetchone()


def buy_business_type(self, user_id, business_type):
    spec = BUSINESSES.get(str(business_type))
    if not spec:
        return False, "❌ Такой бизнес не найден."
    with self.connect() as c:
        u = c.execute("SELECT * FROM users WHERE id=?", (int(user_id),)).fetchone()
        if not u:
            return False, "❌ Игрок не найден."
        if c.execute("SELECT 1 FROM businesses WHERE user_id=?", (int(user_id),)).fetchone():
            return False, "❌ У тебя уже есть бизнес. Сначала развивай текущий."
        if int(u["balance"]) < spec["price"]:
            return False, f"❌ Недостаточно денег. Нужно {_money(spec['price'])}."
        now = int(time.time())
        c.execute("UPDATE users SET balance=balance-? WHERE id=?", (spec["price"], int(user_id)))
        c.execute("INSERT INTO businesses(user_id,type,level,stock,balance,last_tick) VALUES(?,?,?,?,?,?)", (int(user_id), business_type, 1, 0, 0, now))
    return True, f"✅ Бизнес куплен!\n\n{spec['name']}\n💵 Цена: {_money(spec['price'])}\n💰 Доход: {_money(spec['income'])}/мин\n📦 Вместимость: {spec['capacity']:,}".replace(",", " ")


def upgrade_business(self, user_id):
    with self.connect() as c:
        b = c.execute("SELECT * FROM businesses WHERE user_id=?", (int(user_id),)).fetchone()
        if not b:
            return False, "❌ Сначала купи бизнес."
        if int(b["level"]) >= 10:
            return False, "🏆 Бизнес уже достиг максимального 10 уровня."
        spec = _business_spec(b)
        cost = int(spec["price"] * (0.55 + int(b["level"]) * 0.35))
        u = c.execute("SELECT balance FROM users WHERE id=?", (int(user_id),)).fetchone()
        if int(u["balance"]) < cost:
            return False, f"❌ Нужно {_money(cost)} для улучшения."
        new_level = int(b["level"]) + 1
        c.execute("UPDATE users SET balance=balance-? WHERE id=?", (cost, int(user_id)))
        c.execute("UPDATE businesses SET level=? WHERE id=?", (new_level, int(b["id"])))
    return True, f"⬆️ БИЗНЕС УЛУЧШЕН\n\n{spec['name']}\n⭐ Уровень: {new_level}/10\n💰 Доход: {_money(_income(spec,new_level))}/мин\n📦 Вместимость: {_capacity(spec,new_level):,}\n💵 Стоимость: {_money(cost)}".replace(",", " ")


def refill(self, user_id, amount):
    if int(amount) <= 0:
        return "❌ Количество должно быть положительным."
    with self.connect() as c:
        b = c.execute("SELECT * FROM businesses WHERE user_id=?", (int(user_id),)).fetchone()
        if not b:
            return "❌ Сначала купи бизнес."
        tick_business(self, c, b)
        b = c.execute("SELECT * FROM businesses WHERE user_id=?", (int(user_id),)).fetchone()
        spec = _business_spec(b)
        capacity = _capacity(spec, b["level"])
        free = max(0, capacity - int(b["stock"]))
        amount = min(int(amount), free)
        if amount <= 0:
            return "❌ Склад заполнен."
        price = amount * spec["refill"]
        u = c.execute("SELECT balance FROM users WHERE id=?", (int(user_id),)).fetchone()
        if int(u["balance"]) < price:
            return f"❌ Не хватает денег. Нужно {_money(price)}."
        c.execute("UPDATE users SET balance=balance-? WHERE id=?", (price, int(user_id)))
        c.execute("UPDATE businesses SET stock=stock+? WHERE id=?", (amount, int(b["id"])))
    return f"📦 Загружено: {amount:,}\n💵 Стоимость: {_money(price)}".replace(",", " ")


def withdraw(self, user_id):
    with self.connect() as c:
        b = c.execute("SELECT * FROM businesses WHERE user_id=?", (int(user_id),)).fetchone()
        if not b:
            return "❌ Бизнеса нет."
        tick_business(self, c, b)
        b = c.execute("SELECT * FROM businesses WHERE user_id=?", (int(user_id),)).fetchone()
        amount = int(b["balance"])
        if amount <= 0:
            return "💸 Касса пуста."
        c.execute("UPDATE businesses SET balance=0 WHERE id=?", (int(b["id"]),))
        c.execute("UPDATE users SET balance=balance+? WHERE id=?", (amount, int(user_id)))
        c.execute("INSERT INTO transactions(from_user,to_user,amount,type,created_at) VALUES(NULL,?,?,?,?)", (int(user_id), amount, "business_withdraw", int(time.time())))
    return f"💰 Снято: {_money(amount)}"


def transfer(self, user_id, target, amount):
    target_vk = resolve_vk_id(self, target)
    if target_vk is None:
        return "❌ Не удалось найти игрока. Отправь VK ID, ссылку на профиль VK, ник или реферальную ссылку."
    return self._original_transfer(int(user_id), int(target_vk), int(amount))


def attack(self, user_id, target, mode):
    target_vk = resolve_vk_id(self, target)
    if target_vk is None:
        return "❌ Не удалось найти игрока. Отправь VK ID, ссылку на профиль VK, ник или реферальную ссылку."
    return self._original_attack(int(user_id), int(target_vk), mode)


def phone_add(self, user_id, target, nickname=None):
    target_vk = resolve_vk_id(self, target)
    if target_vk is None:
        return False, "❌ Игрок не найден. Можно отправить VK ID, ссылку VK или ник."

    row = self.user_by_vk(target_vk)
    display_name = nickname or (row["nickname"] if row else None)

    # For a direct VK profile URL, prefer the real VK display name instead
    # of the autogenerated Bandit City nickname (Игрок123).
    if not nickname:
        profile = _vk_profile_from_value(self, target)
        if profile:
            display_name = " ".join(
                x for x in (profile.get("first_name"), profile.get("last_name")) if x
            ).strip() or display_name

    return self._original_phone_add(int(user_id), target_vk, display_name)


def apply(bot):
    from admin_panel import AdminPanel
    from game import Game

    # DB extensions.
    Database = bot.db.__class__
    # Give DB extensions access to the already-authenticated VK API session.
    # No token is copied to disk or exposed by this extension.
    Database._vk_api = bot.vk
    Database.resolve_player = resolve_player
    Database.resolve_vk_id = resolve_vk_id
    Database.tick_business = tick_business
    Database.tick_all_businesses = tick_all_businesses
    Database.business = business
    Database.buy_business_type = buy_business_type
    Database.upgrade_business = upgrade_business
    Database.refill = refill

    if not hasattr(Database, "_original_transfer"):
        Database._original_transfer = Database.transfer
        Database._original_attack = Database.attack
        Database._original_phone_add = Database.phone_add
    Database.transfer = transfer
    Database.attack = attack
    Database.phone_add = phone_add

    # Game extensions.
    if not hasattr(Game, "_original_ref_link"):
        Game._original_ref_link = Game.ref_link
        Game._original_profile = Game.profile
    def ref_link(game, uid):
        u = game.db.user(uid)
        group_id = int(getattr(bot, "GROUP_ID", 0) or 0)
        vk_link = f"https://vk.me/club{group_id}?ref={u['ref_code']}" if group_id else f"/start {u['ref_code']}"
        return f"🔗 ТВОЯ РЕФЕРАЛЬНАЯ ССЫЛКА\n\n{vk_link}\n\n/start {u['ref_code']}\n\n🎁 Новый игрок получает $50 000.\n💰 Ты получаешь $100 000 за приглашённого игрока."
    def profile(game, uid):
        return game._original_profile(uid) + "\n\n" + ref_link(game, uid)
    def business_info(game, uid):
        b = game.db.business(uid)
        if not b:
            out = ["🏢 КАТАЛОГ БИЗНЕСА", "", "У каждого игрока может быть один основной бизнес.", "Выбирай направление и потом развивай его до 10 уровня.", ""]
            for spec in BUSINESSES.values():
                out.append(f"{spec['name']}\n💵 { _money(spec['price']) } • 💰 {_money(spec['income'])}/мин\n{spec['desc']}")
            return "\n\n".join(out)
        spec = _business_spec(b)
        level = int(b["level"])
        return (f"🏢 {spec['name']}\n\n🟢 Работает\n⭐ Уровень: {level}/10\n"
                f"💵 Касса: {_money(b['balance'])}\n📦 Склад: {int(b['stock']):,}/{_capacity(spec,level):,}\n"
                f"💰 Доход: {_money(_income(spec,level))}/мин\n📦 Расход сырья: 1 ед./мин\n"
                f"🧾 Пополнение: {_money(spec['refill'])}/ед.\n\n{spec['desc']}").replace(",", " ")
    def buy_business(game, uid):
        return game.buy_business_type(uid, "airport")
    def buy_business_type(game, uid, code):
        ok, result = game.db.buy_business_type(uid, code)
        if ok and not game.db.sms_task_rows(uid,["first_business"]).get("first_business",{}).get("completed",0):
            game.db.sms_task_complete(uid,"first_business")
            game.db.sms_add(uid,"🕴️ Фиксер","Теперь у тебя есть своё дело. Деньги любят тех, кто умеет ими управлять.","first_business",100000,50)
        return result
    def upgrade(game, uid):
        return game.db.upgrade_business(uid)[1]
    Game.ref_link = ref_link
    Game.profile = profile
    Game.business_info = business_info
    Game.buy_business = buy_business
    Game.buy_business_type = buy_business_type
    Game.upgrade_business = upgrade
    Game.refill_stock = lambda game, uid, amount: game.db.refill(uid, amount)
    Game.withdraw_business = lambda game, uid: game.db.withdraw(uid)
    Game.transfer = lambda game, uid, target, amount: game.db.transfer(uid, target, amount)
    Game.attack = lambda game, uid, target, mode: game.db.attack(uid, target, mode)

    # Admin target fields accept IDs, VK links, nicknames and referral links.
    if not hasattr(AdminPanel, "_enhanced_handle"):
        AdminPanel._enhanced_handle = AdminPanel.handle
    original_handle = AdminPanel._enhanced_handle
    def handle(panel, uid, text):
        st = panel.state.get(uid)
        target_states = {"player_lookup","ban","unban","car_list","item_list","appearance_lookup","cash","bank","xp","level","stock","car_delete","item_delete","appearance_set"}
        if st in target_states:
            parts = str(text).split()
            if parts:
                target = panel.db.resolve_vk_id(parts[0])
                if target is not None:
                    parts[0] = str(target)
                    text = " ".join(parts)
        return original_handle(panel, uid, text)
    AdminPanel.handle = handle

    # Patch the player-facing process without touching the stable bot source.
    if hasattr(bot, "_enhanced_process"):
        return
    bot._enhanced_process = bot.process
    original_process = bot.process

    def kb_business():
        return [
            ["🏢 Каталог бизнеса"],
            ["📊 Мой бизнес", "⬆️ Улучшить бизнес"],
            ["📦 Склад", "📦 Пополнить склад"],
            ["💰 Снять деньги"],
            ["🏙️ Главное меню"],
        ]
    bot.kb_business = kb_business

    def process(uid, text):
        raw = str(text or "").strip()
        low = raw.lower()
        user = bot.db.get_or_create_user(uid)

        # Deep/referral links: accept https://vk.me/...?...ref=CODE directly.
        ref = _parse_ref(raw)
        if ref and bot.db.user(user["id"]) is not None:
            if bot.db.needs_onboarding(user["id"]):
                raw = "/start " + ref
            else:
                if bot.game.apply_referral(user["id"], ref):
                    bot.send(uid, "🎁 Реферальная ссылка активирована!\n💵 +$50 000", bot.main_kb(uid))
                else:
                    bot.send(uid, "ℹ️ Реферальная ссылка уже использована или недействительна.", bot.main_kb(uid))
                return

        # Business hub and catalogue.
        if raw == "🏢 Бизнес":
            bot.send(uid, bot.game.business_info(user["id"]), kb_business()); return
        if raw == "🏢 Каталог бизнеса":
            rows=[]
            for code,spec in BUSINESSES.items():
                rows.append([f"🏢 Купить: {spec['short']}"])
            rows.append(["↩️ К бизнесу"])
            bot.send(uid, "🏢 ВЫБОР БИЗНЕСА\n\nВыбери направление:", rows); return
        if raw == "📊 Мой бизнес":
            bot.send(uid, bot.game.business_info(user["id"]), kb_business()); return
        if raw == "⬆️ Улучшить бизнес":
            bot.send(uid, bot.game.upgrade_business(user["id"]), kb_business()); return
        if raw == "↩️ К бизнесу":
            bot.send(uid, bot.game.business_info(user["id"]), kb_business()); return
        if raw.startswith("🏢 Купить: "):
            label = raw.split(": ",1)[1].strip()
            code = next((k for k,v in BUSINESSES.items() if v["short"] == label), None)
            if code:
                bot.send(uid, bot.game.buy_business_type(user["id"], code), kb_business()); return

        # Friendly target syntax for transfers/attacks.
        if low.startswith("/pay ") or low.startswith("/scam ") or low.startswith("/rob "):
            parts = raw.split()
            if len(parts) >= 3 and parts[1] and parts[2].lstrip("-").isdigit():
                amount_or_mode = int(parts[2]) if low.startswith("/pay ") else None
                target = parts[1]
                if low.startswith("/pay "):
                    bot.send(uid, bot.game.transfer(user["id"], target, amount_or_mode), bot.main_kb(uid)); return
                bot.send(uid, bot.game.attack(user["id"], target, "scam" if low.startswith("/scam ") else "rob"), bot.main_kb(uid)); return
            if len(parts) == 2 and not low.startswith("/pay "):
                bot.send(uid, bot.game.attack(user["id"], parts[1], "scam" if low.startswith("/scam ") else "rob"), bot.main_kb(uid)); return
            bot.send(uid, "Использование: /pay ЦЕЛЬ СУММА\nЦель: VK ID, ссылка VK, ник или реферальная ссылка.", bot.main_kb(uid)); return

        # Phone input can also be a link or nickname.
        state = bot.INPUT_STATE.get(uid, {})
        if state.get("mode") in {"phone_add", "phone_remove"}:
            target = bot.db.resolve_vk_id(raw)
            if target is not None:
                # Keep the resolved VK ID as the internal value. This lets
                # https://vk.ru/stasvolk66 work exactly like a numeric ID.
                raw = str(target)

        original_process(uid, raw)

    bot.process = process
