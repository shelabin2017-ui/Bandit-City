"""Multi-business ownership extension for Bandit City.

Applied after enhancements.py. Migrates the legacy businesses table in-place,
preserving existing rows, then provides per-business selection and management.
"""
import time

def apply(bot):
    from enhancements import BUSINESSES, _business_spec, _income, _capacity, _money, tick_business

    db_cls = bot.db.__class__
    if not hasattr(db_cls, "_multi_business_original_init"):
        db_cls._multi_business_original_init = db_cls.init

    # Rebuild only when the legacy UNIQUE(user_id) constraint is present.
    with bot.db.connect() as c:
        cols = c.execute("PRAGMA table_info(businesses)").fetchall()
        indexes = c.execute("PRAGMA index_list(businesses)").fetchall()
        unique_user = False
        for ix in indexes:
            if ix["unique"]:
                names = [r["name"] for r in c.execute("PRAGMA index_info(%s)" % ('"' + ix["name"].replace('"','""') + '"')).fetchall()]
                if names == ["user_id"]:
                    unique_user = True
        c.execute("""CREATE TABLE IF NOT EXISTS business_preferences(
            user_id INTEGER PRIMARY KEY, selected_business_id INTEGER
        )""")
        if unique_user:
            c.execute("ALTER TABLE businesses RENAME TO businesses_legacy_multi_migration")
            c.execute("""CREATE TABLE businesses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                level INTEGER NOT NULL DEFAULT 1,
                stock INTEGER NOT NULL DEFAULT 0,
                balance INTEGER NOT NULL DEFAULT 0,
                last_tick INTEGER NOT NULL
            )""")
            c.execute("""INSERT INTO businesses(id,user_id,type,level,stock,balance,last_tick)
                         SELECT id,user_id,type,level,stock,balance,last_tick
                         FROM businesses_legacy_multi_migration""")
            c.execute("DROP TABLE businesses_legacy_multi_migration")
            c.execute("CREATE INDEX IF NOT EXISTS idx_businesses_user_id ON businesses(user_id)")
        c.execute("""INSERT OR IGNORE INTO business_preferences(user_id,selected_business_id)
                     SELECT user_id, MIN(id) FROM businesses GROUP BY user_id""")

    def list_businesses(self, user_id):
        with self.connect() as c:
            rows = c.execute("SELECT * FROM businesses WHERE user_id=? ORDER BY id", (int(user_id),)).fetchall()
            for row in rows:
                tick_business(self, c, row)
            return c.execute("SELECT * FROM businesses WHERE user_id=? ORDER BY id", (int(user_id),)).fetchall()

    def selected_business(self, user_id):
        rows = list_businesses(self, user_id)
        if not rows:
            return None
        with self.connect() as c:
            pref = c.execute("SELECT selected_business_id FROM business_preferences WHERE user_id=?", (int(user_id),)).fetchone()
            selected_id = int(pref["selected_business_id"]) if pref and pref["selected_business_id"] else None
            chosen = next((r for r in rows if int(r["id"]) == selected_id), rows[0])
            c.execute("INSERT INTO business_preferences(user_id,selected_business_id) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET selected_business_id=excluded.selected_business_id", (int(user_id), int(chosen["id"])))
            return c.execute("SELECT * FROM businesses WHERE id=?", (int(chosen["id"]),)).fetchone()

    def select_business(self, user_id, business_id):
        with self.connect() as c:
            row = c.execute("SELECT id FROM businesses WHERE id=? AND user_id=?", (int(business_id), int(user_id))).fetchone()
            if not row:
                return False
            c.execute("INSERT INTO business_preferences(user_id,selected_business_id) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET selected_business_id=excluded.selected_business_id", (int(user_id), int(business_id)))
            return True

    def business(self, user_id):
        return selected_business(self, user_id)

    def buy_business_type(self, user_id, business_type):
        spec = BUSINESSES.get(str(business_type))
        if not spec:
            return False, "❌ Такой бизнес не найден."
        with self.connect() as c:
            u = c.execute("SELECT * FROM users WHERE id=?", (int(user_id),)).fetchone()
            if not u:
                return False, "❌ Игрок не найден."
            if c.execute("SELECT 1 FROM businesses WHERE user_id=? AND type=?", (int(user_id), str(business_type))).fetchone():
                return False, "❌ У тебя уже есть бизнес этого типа."
            if int(u["balance"]) < spec["price"]:
                return False, f"❌ Недостаточно денег. Нужно {_money(spec['price'])}."
            now = int(time.time())
            c.execute("UPDATE users SET balance=balance-? WHERE id=?", (spec["price"], int(user_id)))
            cur = c.execute("INSERT INTO businesses(user_id,type,level,stock,balance,last_tick) VALUES(?,?,?,?,?,?)", (int(user_id), str(business_type), 1, 0, 0, now))
            business_id = cur.lastrowid
            c.execute("INSERT INTO business_preferences(user_id,selected_business_id) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET selected_business_id=excluded.selected_business_id", (int(user_id), int(business_id)))
        return True, f"✅ Бизнес куплен!\n\n{spec['name']}\n💵 Цена: {_money(spec['price'])}\n💰 Доход: {_money(spec['income'])}/мин\n📦 Вместимость: {spec['capacity']:,}".replace(",", " ")

    def upgrade_business(self, user_id):
        b = selected_business(self, user_id)
        if not b:
            return False, "❌ Сначала купи бизнес."
        with self.connect() as c:
            b = c.execute("SELECT * FROM businesses WHERE id=? AND user_id=?", (int(b["id"]), int(user_id))).fetchone()
            if int(b["level"]) >= 10:
                return False, "🏆 Бизнес уже достиг максимального 10 уровня."
            spec = _business_spec(b)
            cost = int(spec["price"] * (0.55 + int(b["level"]) * 0.35))
            u = c.execute("SELECT balance FROM users WHERE id=?", (int(user_id),)).fetchone()
            if int(u["balance"]) < cost:
                return False, f"❌ Нужно {_money(cost)} для улучшения."
            level = int(b["level"]) + 1
            c.execute("UPDATE users SET balance=balance-? WHERE id=?", (cost, int(user_id)))
            c.execute("UPDATE businesses SET level=? WHERE id=?", (level, int(b["id"])))
        return True, f"⬆️ БИЗНЕС УЛУЧШЕН\n\n{spec['name']}\n⭐ Уровень: {level}/10\n💰 Доход: {_money(_income(spec,level))}/мин\n📦 Вместимость: {_capacity(spec,level):,}\n💵 Стоимость: {_money(cost)}".replace(",", " ")

    def refill(self, user_id, amount):
        if int(amount) <= 0:
            return "❌ Количество должно быть положительным."
        b = selected_business(self, user_id)
        if not b:
            return "❌ Сначала купи бизнес."
        with self.connect() as c:
            b = c.execute("SELECT * FROM businesses WHERE id=? AND user_id=?", (int(b["id"]), int(user_id))).fetchone()
            tick_business(self, c, b)
            b = c.execute("SELECT * FROM businesses WHERE id=?", (int(b["id"]),)).fetchone()
            spec = _business_spec(b)
            free = max(0, _capacity(spec,b["level"]) - int(b["stock"]))
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
        b = selected_business(self, user_id)
        if not b:
            return "💸 Бизнеса нет."
        with self.connect() as c:
            b = c.execute("SELECT * FROM businesses WHERE id=? AND user_id=?", (int(b["id"]), int(user_id))).fetchone()
            tick_business(self, c, b)
            b = c.execute("SELECT * FROM businesses WHERE id=?", (int(b["id"]),)).fetchone()
            amount = int(b["balance"])
            if amount <= 0:
                return "💸 Касса пуста."
            c.execute("UPDATE businesses SET balance=0 WHERE id=?", (int(b["id"]),))
            c.execute("UPDATE users SET balance=balance+? WHERE id=?", (amount, int(user_id)))
            c.execute("INSERT INTO transactions(from_user,to_user,amount,type,created_at) VALUES(NULL,?,?,?,?)", (int(user_id), amount, "business_withdraw", int(time.time())))
        return f"💰 Снято: {_money(amount)}"

    db_cls.list_businesses = list_businesses
    db_cls.selected_business = selected_business
    db_cls.select_business = select_business
    db_cls.business = business
    db_cls.buy_business_type = buy_business_type
    db_cls.upgrade_business = upgrade_business
    db_cls.refill = refill
    db_cls.withdraw = withdraw

    # All owned businesses earn independently.
    def tick_all_businesses(self):
        with self.connect() as c:
            for row in c.execute("SELECT * FROM businesses").fetchall():
                tick_business(self, c, row)
    db_cls.tick_all_businesses = tick_all_businesses

    from game import Game
    def business_info(game, uid):
        rows = game.db.list_businesses(uid)
        if not rows:
            out = ["🏢 КАТАЛОГ БИЗНЕСА", "", "Можно владеть несколькими предприятиями одновременно.", ""]
            for spec in BUSINESSES.values():
                out.append(f"{spec['name']}\n💵 {_money(spec['price'])} • 💰 {_money(spec['income'])}/мин\n{spec['desc']}")
            return "\n\n".join(out)
        selected = game.db.selected_business(uid)
        out = [f"🏢 ТВОИ БИЗНЕСЫ: {len(rows)}", "Ниже можно выбрать предприятие для управления.", ""]
        for row in rows:
            spec = _business_spec(row)
            marker = "👉 " if int(row["id"]) == int(selected["id"]) else ""
            out.append(f"{marker}#{row['id']} {spec['name']} • ур. {row['level']} • касса {_money(row['balance'])} • склад {row['stock']}/{_capacity(spec,row['level'])}")
        spec = _business_spec(selected)
        out += ["", f"🎯 ВЫБРАН: #{selected['id']} {spec['name']}", f"⭐ Уровень: {selected['level']}/10", f"💵 Касса: {_money(selected['balance'])}", f"📦 Склад: {selected['stock']:,}/{_capacity(spec,selected['level']):,}", f"💰 Доход: {_money(_income(spec,selected['level']))}/мин", f"🧾 Сырьё: {_money(spec['refill'])}/ед.", spec["desc"]]
        return "\n".join(out).replace(",", " ")
    Game.business_info = business_info

    # Add business selection buttons and route them before the original processor.
    original_process = bot.process
    def kb_business():
        return [["🏢 Каталог бизнеса"], ["📊 Мой бизнес", "⬆️ Улучшить бизнес"], ["📦 Склад", "📦 Пополнить склад"], ["💰 Снять деньги"], ["🏙️ Главное меню"]]
    bot.kb_business = kb_business
    def process(uid, text):
        raw = str(text or "").strip()
        if raw == "🏢 Мои предприятия":
            rows = bot.db.list_businesses(bot.db.get_or_create_user(uid)["id"])
            buttons = [[f"🎯 Выбрать бизнес #{r['id']}"] for r in rows]
            buttons.append(["↩️ К бизнесу"])
            bot.send(uid, "🏢 ВЫБЕРИ ПРЕДПРИЯТИЕ ДЛЯ УПРАВЛЕНИЯ", buttons)
            return
        if raw.startswith("🎯 Выбрать бизнес #"):
            try:
                bid = int(raw.rsplit("#",1)[1])
                user = bot.db.get_or_create_user(uid)
                if bot.db.select_business(user["id"], bid):
                    bot.send(uid, bot.game.business_info(user["id"]), kb_business())
                else:
                    bot.send(uid, "❌ Это предприятие не найдено.", kb_business())
            except (ValueError, TypeError):
                bot.send(uid, "❌ Неверный номер предприятия.", kb_business())
            return
        if raw == "🏢 Каталог бизнеса":
            rows = [[f"🏢 Купить: {spec['short']}"] for spec in BUSINESSES.values()]
            rows.append(["🏢 Мои предприятия", "↩️ К бизнесу"])
            bot.send(uid, "🏢 КАТАЛОГ БИЗНЕСА\n\nВыбирай разные предприятия. Повторно купить один и тот же тип нельзя.", rows)
            return
        if raw == "📊 Мой бизнес":
            user = bot.db.get_or_create_user(uid)
            rows = bot.db.list_businesses(user["id"])
            buttons = [["🏢 Мои предприятия"]] if rows else []
            buttons += [["🏢 Каталог бизнеса"], ["🏙️ Главное меню"]]
            bot.send(uid, bot.game.business_info(user["id"]), buttons)
            return
        if raw == "↩️ К бизнесу":
            user = bot.db.get_or_create_user(uid)
            bot.send(uid, bot.game.business_info(user["id"]), kb_business())
            return
        if raw == "🏢 Бизнес":
            user = bot.db.get_or_create_user(uid)
            bot.send(uid, bot.game.business_info(user["id"]), kb_business())
            return
        return original_process(uid, raw)
    bot.process = process
