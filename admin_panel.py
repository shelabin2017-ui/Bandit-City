import time
from roles import Role


class AdminPanel:
    """Inline admin console. It uses the existing SQLite schema and adds no external dependency."""
    def __init__(self, db, game, admin_ids, keyboard_factory=None, roles=None, role_ui=None):
        self.db = db
        self.game = game
        self.admin_ids = set(admin_ids)
        self.keyboard_factory = keyboard_factory
        self.roles = roles
        self.role_ui = role_ui
        self.state = {}

    def role(self, uid):
        if self.roles is None:
            return Role.ADMIN if int(uid) in self.admin_ids else Role.PLAYER
        return self.roles.role(uid)

    def is_admin(self, uid):
        return int(uid) in self.admin_ids or self.role(uid) >= Role.ADMIN

    def is_moderator(self, uid):
        return self.role(uid) >= Role.MODERATOR

    def _moderator_allowed(self, text):
        if self.role(self._home_uid) >= Role.ADMIN:
            return True

        # Moderators may inspect players and perform moderation actions only.
        # Never let an active admin state make arbitrary input reachable by a moderator.
        st = self.state.get(self._home_uid)
        if st in {"player_lookup", "ban", "unban"}:
            return text.strip().isdigit()

        allowed = {
            "🛡 Панель модератора",
            "👥 Игроки",
            "🔎 Карточка игрока",
            "🛡 Безопасность",
            "🧾 Журнал",
            "🏙️ Главное меню",
        }
        return (
            text in allowed
            or text.startswith("/aban ")
            or text.startswith("/aunban ")
            or text.startswith("/aplayer ")
            or text == "/adminlogs"
        )

    def home(self):
        if self.role_ui is not None:
            return self.role_ui.home(self._home_uid)
        return (
            "👑 BANDIT CITY • ЦЕНТР УПРАВЛЕНИЯ\n\n"
            "Здесь можно управлять экономикой, игроками, XP, бизнесом, машинами, вещами, безопасностью, промокодами и городом.\n\n"
            "🔐 Панель доступна только ADMIN_IDS.",
            [
                ["📊 Статистика", "👥 Игроки"],
                ["💰 Экономика", "⭐ XP / Уровень"],
                ["🏢 Бизнес", "🚗 Машины"],
                ["🎒 Вещи", "🛡 Безопасность"],
                ["📢 Рассылка", "🎟 Промокоды"],
                ["🎨 Внешность", "🧾 Журнал"],
                ["🎪 Ивенты", "⚙️ Настройки"],
                ["🏙️ Главное меню"],
            ],
        )

    def _conn(self):
        return self.db.connect()

    def _find(self, vk_id):
        with self._conn() as c:
            return c.execute("SELECT * FROM users WHERE vk_id=?", (int(vk_id),)).fetchone()

    def _players(self, limit=10):
        with self._conn() as c:
            return c.execute(
                "SELECT vk_id,balance,bank,level,xp,banned,created_at FROM users ORDER BY balance+bank DESC LIMIT ?",
                (int(limit),),
            ).fetchall()

    def _log(self, uid, action, target=None, value=None):
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS admin_logs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_vk INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_vk INTEGER,
                value TEXT,
                created_at INTEGER NOT NULL
            )""")
            c.execute(
                "INSERT INTO admin_logs(admin_vk,action,target_vk,value,created_at) VALUES(?,?,?,?,?)",
                (int(uid), action, target, None if value is None else str(value), int(time.time())),
            )

    def _set_cash(self, vk_id, amount):
        with self._conn() as c:
            row = c.execute("SELECT id FROM users WHERE vk_id=?", (int(vk_id),)).fetchone()
            if not row:
                return False
            c.execute("UPDATE users SET balance=? WHERE id=?", (int(amount), row["id"]))
            return True

    def _set_bank(self, vk_id, amount):
        with self._conn() as c:
            row = c.execute("SELECT id FROM users WHERE vk_id=?", (int(vk_id),)).fetchone()
            if not row:
                return False
            c.execute("UPDATE users SET bank=? WHERE id=?", (int(amount), row["id"]))
            return True

    def _set_xp(self, vk_id, xp):
        with self._conn() as c:
            row = c.execute("SELECT id FROM users WHERE vk_id=?", (int(vk_id),)).fetchone()
            if not row:
                return False
            xp = max(0, int(xp))
            c.execute("UPDATE users SET xp=?,level=? WHERE id=?", (xp, xp // 100 + 1, row["id"]))
            return True

    def _set_level(self, vk_id, level):
        with self._conn() as c:
            row = c.execute("SELECT id FROM users WHERE vk_id=?", (int(vk_id),)).fetchone()
            if not row:
                return False
            c.execute("UPDATE users SET level=? WHERE id=?", (max(1, int(level)), row["id"]))
            return True

    def _set_stock(self, vk_id, stock):
        with self._conn() as c:
            row = c.execute("SELECT id FROM users WHERE vk_id=?", (int(vk_id),)).fetchone()
            if not row:
                return False
            business = c.execute("SELECT id FROM businesses WHERE user_id=?", (row["id"],)).fetchone()
            if not business:
                return False
            c.execute("UPDATE businesses SET stock=? WHERE id=?", (max(0, int(stock)), business["id"]))
            return True

    def _toggle_ban(self, vk_id, banned):
        with self._conn() as c:
            cur = c.execute("UPDATE users SET banned=? WHERE vk_id=?", (1 if banned else 0, int(vk_id)))
            return cur.rowcount > 0

    def _stats(self):
        with self._conn() as c:
            users = c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
            started = c.execute("SELECT COUNT(*) n FROM users WHERE onboarding_done=1").fetchone()["n"]
            cash = c.execute("SELECT COALESCE(SUM(balance),0) n FROM users").fetchone()["n"]
            bank = c.execute("SELECT COALESCE(SUM(bank),0) n FROM users").fetchone()["n"]
            businesses = c.execute("SELECT COUNT(*) n FROM businesses").fetchone()["n"]
            cars = c.execute("SELECT COUNT(*) n FROM cars").fetchone()["n"]
            items = c.execute("SELECT COUNT(*) n FROM items").fetchone()["n"]
            banned = c.execute("SELECT COUNT(*) n FROM users WHERE banned=1").fetchone()["n"]
            tx = c.execute("SELECT COUNT(*) n FROM transactions").fetchone()["n"]
        return (
            "📊 BANDIT CITY • СТАТИСТИКА\n\n"
            f"👥 Игроков: {users}\n✅ Прошли старт: {started}\n⛔ В бане: {banned}\n"
            f"💵 Денег у игроков: ${cash:,}\n🏦 В банках: ${bank:,}\n"
            f"🏢 Бизнесов: {businesses}\n🚗 Машин: {cars}\n🎒 Вещей: {items}\n🧾 Транзакций: {tx}"
        ).replace(",", " ")

    def _logs(self, limit=15):
        with self._conn() as c:
            rows=c.execute("SELECT admin_vk,action,target_vk,value,created_at FROM admin_logs ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        if not rows:
            return "🧾 Журнал действий пока пуст."
        body=["🧾 ЖУРНАЛ АДМИНИСТРАТОРА",""]
        for r in rows:
            body.append("👑 {} • {} • {} • {}".format(r["admin_vk"], r["action"], r["target_vk"] or "-", r["value"] or "-"))
        return "\n".join(body)

    def _cars(self, vk_id):
        with self._conn() as c:
            u=c.execute("SELECT id FROM users WHERE vk_id=?", (int(vk_id),)).fetchone()
            return None if not u else c.execute("SELECT id,model,category,speed,price FROM cars WHERE user_id=? ORDER BY id DESC", (u["id"],)).fetchall()

    def _items(self, vk_id):
        with self._conn() as c:
            u=c.execute("SELECT id FROM users WHERE vk_id=?", (int(vk_id),)).fetchone()
            return None if not u else c.execute("SELECT id,name,price FROM items WHERE user_id=? ORDER BY id DESC", (u["id"],)).fetchall()
    def handle(self, uid, text):
        if not self.is_admin(uid) and not self.is_moderator(uid):
            return False, "", []
        self._home_uid = int(uid)
        text = text.strip()
        if not self._moderator_allowed(text):
            return False, "", []


        st = self.state.get(uid)
        if st:
            if text in ("❌ Отмена", "отмена") and st != "broadcast_confirm":
                self.state.pop(uid, None)
                return True, "❌ Операция отменена.", [["👑 Админ-панель"]]
            try:
                if st == "promo_toggle":
                    code = text.strip().upper()
                    with self._conn() as c:
                        cur = c.execute("UPDATE promo_codes SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE code=?", (code,))
                    self.state.pop(uid, None)
                    if not cur.rowcount:
                        return True, "❌ Промокод не найден.", [["🎟 Промокоды"], ["👑 Админ-панель"]]
                    self._log(uid, "promo_toggle", None, code)
                    return True, "✅ Промокод переключён.", [["🎟 Промокоды"], ["👑 Админ-панель"]]
                if st == "promo_add":
                    parts = [x.strip() for x in text.split("|")]
                    if len(parts) not in (5, 7):
                        return True, "❌ Формат: CODE|TITLE|CASH|XP|MAX_USES[|ITEM|SLOT]", [["👑 Админ-панель"]]
                    code, title, cash, xp, max_uses = parts[:5]
                    item = parts[5] if len(parts) == 7 else None
                    slot = parts[6] if len(parts) == 7 else None
                    try:
                        cash, xp, max_uses = int(cash), int(xp), int(max_uses)
                    except ValueError:
                        return True, "❌ CASH, XP и MAX_USES должны быть числами.", [["👑 Админ-панель"]]
                    with self._conn() as c:
                        c.execute("INSERT OR REPLACE INTO promo_codes(code,title,reward_cash,reward_xp,reward_item,reward_slot,max_uses,used_count,active) VALUES(?,?,?,?,?,?,?,0,1)", (code.upper(), title, cash, xp, item or None, slot or None, max_uses))
                    self._log(uid, "promo_add", None, code.upper())
                    self.state.pop(uid, None)
                    return True, "✅ Промокод создан и активирован.", [["🎟 Промокоды"], ["👑 Админ-панель"]]
                if st == "appearance_lookup":
                    target = int(text)
                    self.state.pop(uid, None)
                    row = self._find(target)
                    if not row:
                        return True, "❌ Игрок не найден.", [["🎨 Внешность"], ["👑 Админ-панель"]]
                    a = self.db.appearance(row["id"])
                    msg = "🎨 ВНЕШНОСТЬ VK {}\n\n💇 {}\n👕 {}\n👖 {}\n🥾 {}\n🧢 {}\n💍 {}\n🌆 {}".format(target, a["hair"], a["clothes"], a["pants"], a["shoes"], a["head"], a["accessory"], a["background"])
                    return True, msg, [["✏️ Изменить внешность"], ["🎨 Внешность"], ["👑 Админ-панель"]]
                if st == "appearance_set":
                    parts = text.split(maxsplit=3)
                    if len(parts) < 3:
                        return True, "❌ Формат: VK_ID SLOT VALUE", [["🎨 Внешность"], ["👑 Админ-панель"]]
                    target, slot = int(parts[0]), parts[1]
                    value = parts[2] if len(parts) == 3 else parts[2] + " " + parts[3]
                    if slot not in {"hair","clothes","pants","shoes","head","accessory","background"} or not value.strip():
                        return True, "❌ Недопустимый слот.", [["🎨 Внешность"], ["👑 Админ-панель"]]
                    row = self._find(target)
                    if not row:
                        self.state.pop(uid, None)
                        return True, "❌ Игрок не найден.", [["🎨 Внешность"], ["👑 Админ-панель"]]
                    self.db.set_appearance(row["id"], **{slot: value.strip()})
                    self._log(uid, "appearance_set", target, slot + "=" + value.strip())
                    self.state.pop(uid, None)
                    return True, "✅ Внешность изменена.", [["🎨 Внешность"], ["👑 Админ-панель"]]
                if st == "broadcast_text":
                    self.state[uid] = ("broadcast_confirm", text.strip())
                    return True, "📢 ПРЕДПРОСМОТР\n\n" + text.strip(), [["✅ Отправить","❌ Отмена"],["👑 Админ-панель"]]
                if isinstance(st, tuple) and st[0] == "broadcast_confirm":
                    if text == "❌ Отмена":
                        self.state.pop(uid, None)
                        return True, "❌ Отменено.", [["👑 Админ-панель"]]
                    if text == "✅ Отправить":
                        payload = st[1]
                        self.state.pop(uid, None)
                        return True, "__BROADCAST_EXEC__|" + payload, [["👑 Админ-панель"]]
                if st == "player_lookup":
                    target=int(text); self.state.pop(uid,None); r=self._find(target)
                    if not r: return True,"❌ Игрок не найден.",[["👥 Игроки"],["👑 Админ-панель"]]
                    msg=("👤 ИГРОК {}\n\n💵 {}\n🏦 {}\n⭐ Уровень {}\n✨ XP {}\n⛔ Бан: {}").format(target,r["balance"],r["bank"],r["level"],r["xp"],"да" if r["banned"] else "нет").replace(","," ")
                    if self.role(uid) < Role.ADMIN:
                        rows=[["⛔ Заблокировать","✅ Разблокировать"],["👥 Игроки"],["🛡 Панель модератора"]]
                    else:
                        rows=[["💵 Изменить наличные","🏦 Изменить банк"],["⭐ Изменить XP","🎚 Изменить уровень"],["⛔ Заблокировать","✅ Разблокировать"],["👥 Игроки"],["👑 Админ-панель"]]
                    return True,msg,rows
                if st in ("cash","bank","xp","level","stock"):
                    parts=text.split(); target=int(parts[0]); amount=int(parts[1])
                    if st=="cash": ok=self._set_cash(target,amount); action="set_cash"
                    elif st=="bank": ok=self._set_bank(target,amount); action="set_bank"
                    elif st=="xp": ok=self._set_xp(target,amount); action="set_xp"
                    elif st=="level": ok=self._set_level(target,amount); action="set_level"
                    else: ok=self._set_stock(target,amount); action="set_stock"
                    self._log(uid,action,target,amount); self.state.pop(uid,None)
                    return True,"✅ Изменено." if ok else "❌ Игрок или бизнес не найден.",[["👥 Игроки"],["👑 Админ-панель"]]
                if st in ("ban","unban"):
                    target=int(text); ok=self._toggle_ban(target,st=="ban"); self._log(uid,st,target); self.state.pop(uid,None)
                    return True,("⛔ Игрок заблокирован." if st=="ban" else "✅ Игрок разблокирован.") if ok else "❌ Игрок не найден.",[["👥 Игроки"],["👑 Админ-панель"]]
                if st=="car_list":
                    target=int(text); self.state.pop(uid,None); rows=self._cars(target)
                    if rows is None: return True,"❌ Игрок не найден.",[["🚗 Машины"],["👑 Админ-панель"]]
                    body=["🚗 МАШИНЫ VK "+str(target)]+["#{} • {} • {} • ⚡{} • {}".format(r["id"],r["model"],r["category"],r["speed"],r["price"]).replace(","," ") for r in rows]
                    return True,"\n".join(body),[["🗑 Удалить машину"],["🚗 Машины"],["👑 Админ-панель"]]
                if st=="car_delete":
                    target,car_id=map(int,text.split()[:2])
                    with self._conn() as c: cur=c.execute("DELETE FROM cars WHERE id=? AND user_id=(SELECT id FROM users WHERE vk_id=?)",(car_id,target))
                    self._log(uid,"car_delete",target,car_id); self.state.pop(uid,None)
                    return True,"✅ Машина удалена." if cur.rowcount else "❌ Машина не найдена.",[["🚗 Машины"],["👑 Админ-панель"]]
                if st=="item_list":
                    target=int(text); self.state.pop(uid,None); rows=self._items(target)
                    if rows is None: return True,"❌ Игрок не найден.",[["🎒 Вещи"],["👑 Админ-панель"]]
                    body=["🎒 ВЕЩИ VK "+str(target)]+["#{} • {} • {}".format(r["id"],r["name"],r["price"]).replace(","," ") for r in rows]
                    return True,"\n".join(body),[["🗑 Удалить вещь"],["🎒 Вещи"],["👑 Админ-панель"]]
                if st=="item_delete":
                    target,item_id=map(int,text.split()[:2])
                    with self._conn() as c: cur=c.execute("DELETE FROM items WHERE id=? AND user_id=(SELECT id FROM users WHERE vk_id=?)",(item_id,target))
                    self._log(uid,"item_delete",target,item_id); self.state.pop(uid,None)
                    return True,"✅ Вещь удалена." if cur.rowcount else "❌ Вещь не найдена.",[["🎒 Вещи"],["👑 Админ-панель"]]
            except (ValueError,IndexError):
                return True,"❌ Неверный формат. Попробуй ещё раз.",[["👑 Админ-панель"]]

        if text in ("👑 Центр владельца", "⚙️ Панель администратора", "🛡 Панель модератора"):
            return True, *self.role_ui.home(uid)

        if text == "📋 Список персонала":
            if self.role(uid) < Role.OWNER:
                return True, "⛔ Доступ только владельцу.", [["🏙️ Главное меню"]]
            return True, self.role_ui.staff_list(), [["👑 Центр владельца"]]

        if text in ("➕ Выдать роль", "🔄 Изменить роль", "➖ Снять роль"):
            if self.role(uid) < Role.OWNER:
                return True, "⛔ Доступ только владельцу.", [["🏙️ Главное меню"]]
            if text == "➕ Выдать роль":
                self.state[uid] = "grant_role"
                return True, "➕ ВЫДАТЬ РОЛЬ\n\nВведи: VK_ID РОЛЬ\nРоли: admin, moderator, player", [["👑 Центр владельца"]]
            if text == "🔄 Изменить роль":
                self.state[uid] = "change_role"
                return True, "🔄 ИЗМЕНИТЬ РОЛЬ\n\nВведи: VK_ID РОЛЬ\nРоли: admin, moderator, player", [["👑 Центр владельца"]]
            self.state[uid] = "revoke_role"
            return True, "➖ СНЯТЬ РОЛЬ\n\nВведи VK_ID", [["👑 Центр владельца"]]

        if text == "🧾 Журнал ролей":
            if self.role(uid) < Role.OWNER:
                return True, "⛔ Доступ только владельцу.", [["🏙️ Главное меню"]]
            return True, self.roles.logs_text(), [["👑 Центр владельца"]]

        if text in ("👑 Админ-панель", "👑 Админка"):
            self.state.pop(uid, None)
            return True, *self.home()
        if text == "🏙️ Главное меню":
            self.state.pop(uid, None)
            return True, "__MAIN__", []

        if text=="🔎 Найти игрока":
            self.state[uid]="player_lookup"
            return True,"🔎 Введи VK ID игрока.",[["👑 Админ-панель"]]
        if text=="💵 Наличные":
            self.state[uid]="cash"
            return True,"💵 Введи: VK_ID СУММА",[["👑 Админ-панель"]]
        if text=="🏦 Банк":
            self.state[uid]="bank"
            return True,"🏦 Введи: VK_ID СУММА",[["👑 Админ-панель"]]
        if text=="⭐ XP":
            self.state[uid]="xp"
            return True,"⭐ Введи: VK_ID XP",[["👑 Админ-панель"]]
        if text=="🎚 Уровень":
            self.state[uid]="level"
            return True,"🎚 Введи: VK_ID УРОВЕНЬ",[["👑 Админ-панель"]]
        if text=="📦 Изменить склад":
            self.state[uid]="stock"
            return True,"📦 Введи: VK_ID КОЛИЧЕСТВО",[["👑 Админ-панель"]]
        if text=="📋 Машины игрока":
            self.state[uid]="car_list"
            return True,"🚗 Введи VK ID игрока.",[["👑 Админ-панель"]]
        if text=="🗑 Удалить машину":
            self.state[uid]="car_delete"
            return True,"🗑 Введи: VK_ID ID_МАШИНЫ",[["👑 Админ-панель"]]
        if text=="📋 Вещи игрока":
            self.state[uid]="item_list"
            return True,"🎒 Введи VK ID игрока.",[["👑 Админ-панель"]]
        if text=="🗑 Удалить вещь":
            self.state[uid]="item_delete"
            return True,"🗑 Введи: VK_ID ID_ВЕЩИ",[["👑 Админ-панель"]]
        if text=="🔎 Карточка игрока":
            self.state[uid]="player_lookup"
            home = "🛡 Панель модератора" if self.role(uid) < Role.ADMIN else "👑 Админ-панель"
            return True,"🔎 Введи VK ID игрока.",[[home]]
        if text=="⛔ Заблокировать":
            self.state[uid]="ban"
            return True,"⛔ Введи VK ID игрока.",[["👑 Админ-панель"]]
        if text=="✅ Разблокировать":
            self.state[uid]="unban"
            return True,"✅ Введи VK ID игрока.",[["👑 Админ-панель"]]

        if text == "📊 Статистика":
            return True, self._stats(), [["👑 Админ-панель"], ["🏙️ Главное меню"]]
        if text == "👥 Игроки":
            rows = self._players(12)
            body = ["👥 ИГРОКИ • TOP"]
            for i, r in enumerate(rows, 1):
                body.append(f"{i}. VK {r['vk_id']} • 💵 {r['balance']:,} • 🏦 {r['bank']:,} • ⭐{r['level']}".replace(",", " "))
            body.append("\n🔎 Нажми «🔎 Карточка игрока» для поиска.")
            home = "🛡 Панель модератора" if self.role(uid) < Role.ADMIN else "👑 Админ-панель"
            return True, "\n".join(body), [["🔎 Карточка игрока"], [home], ["🏙️ Главное меню"]]
        if text == "💰 Экономика":
            return True, "💰 ЭКОНОМИКА\n\nВыбери действие.", [["💵 Наличные", "🏦 Банк"], ["👑 Админ-панель"]]
        if text in ("💵 Наличные", "🏦 Банк"):
            self.state[uid] = "cash" if text == "💵 Наличные" else "bank"
            return True, "Введи: VK_ID СУММА\nПример: 123456789 37500\n\nДля отмены: отмена", [["👑 Админ-панель"]]
        if text == "⭐ XP / Уровень":
            return True, "⭐ XP / УРОВЕНЬ\n\nВыбери действие.", [["⭐ XP", "🎚 Уровень"], ["👑 Админ-панель"]]
        if text == "🏢 Бизнес":
            return True, "🏢 БИЗНЕС\n\nВыбери действие.", [["📦 Изменить склад"], ["👑 Админ-панель"]]
        if text == "🚗 Машины":
            return True, "🚗 МАШИНЫ\n\nВыбери действие.", [["📋 Машины игрока", "🗑 Удалить машину"], ["👑 Админ-панель"]]
        if text == "🎒 Вещи":
            return True, "🎒 ВЕЩИ\n\nВыбери действие.", [["📋 Вещи игрока", "🗑 Удалить вещь"], ["👑 Админ-панель"]]
        if text == "🛡 Безопасность":
            return True, "🛡 БЕЗОПАСНОСТЬ\n\nВыбери действие.", [["🔎 Карточка игрока"], ["⛔ Заблокировать", "✅ Разблокировать"], ["👑 Админ-панель"]]
        if text == "📢 Рассылка":
            if self.role(uid) < Role.ADMIN:
                return True, "⛔ Доступ только ADMIN.", [["🏙️ Главное меню"]]
            return True, "📢 РАССЫЛКА\n\nСоздай сообщение и подтверди отправку.", [["✍️ Создать рассылку"], ["👑 Админ-панель"]]
        if text == "✍️ Создать рассылку":
            self.state[uid] = "broadcast_text"
            return True, "✍️ ВВЕДИ ТЕКСТ РАССЫЛКИ", [["❌ Отмена"], ["👑 Админ-панель"]]
        if text == "🎟 Промокоды":
            if self.role(uid) < Role.ADMIN:
                return True, "⛔ Доступ только ADMIN.", [["🏙️ Главное меню"]]
            return True, "🎟 ПРОМОКОДЫ\n\nВыбери действие.", [["➕ Создать промокод", "📋 Список промокодов"], ["🔄 Переключить промокод"], ["👑 Админ-панель"]]
        if text == "➕ Создать промокод":
            self.state[uid] = "promo_add"
            return True, "➕ Формат: CODE|TITLE|CASH|XP|MAX_USES[|ITEM|SLOT]", [["❌ Отмена"], ["👑 Админ-панель"]]
        if text == "📋 Список промокодов":
            with self._conn() as c:
                rows = c.execute("SELECT code,title,reward_cash,reward_xp,used_count,max_uses,active FROM promo_codes ORDER BY code").fetchall()
            body = ["🎟 СПИСОК ПРОМОКОДОВ", ""]
            for r in rows:
                body.append("{} • {} • ${} • +{} XP • {}/{}".format(r["code"], "🟢" if r["active"] else "🔴", str(r["reward_cash"]).replace(","," "), r["reward_xp"], r["used_count"], r["max_uses"] or "∞"))
            return True, "\n".join(body), [["🎟 Промокоды"], ["👑 Админ-панель"]]
        if text == "🔄 Переключить промокод":
            self.state[uid] = "promo_toggle"
            return True, "🔄 Введи код промокода.", [["❌ Отмена"], ["👑 Админ-панель"]]
        if text in ("⚙️ Настройки", "⚙️ Технический режим"):
            with self._conn() as c:
                row = c.execute("SELECT value FROM settings WHERE key='maintenance_mode'").fetchone()
            mode = row["value"] if row else "0"
            status = "ВКЛ" if mode == "1" else "ВЫКЛ"
            return True, (
                "⚙️ НАСТРОЙКИ\n\n"
                f"🔧 Технический режим: {status}\n\n"
                "Выбери действие ниже."
            ), [
                ["🟢 Включить техрежим"],
                ["🔴 Выключить техрежим"],
                ["👑 Админ-панель"],
            ]

        if text == "🟢 Включить техрежим":
            with self._conn() as c:
                c.execute(
                    "INSERT INTO settings(key,value) VALUES('maintenance_mode',?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    ("1",)
                )
            self._log(uid, "maintenance", None, "on")
            return True, (
                "🔧 ТЕХНИЧЕСКИЙ РЕЖИМ\n\n"
                "🟢 Технический режим включён.\n\n"
                "👥 Обычные игроки увидят сообщение о технических работах.\n"
                "👑 Администратор продолжает иметь доступ к боту."
            ), [
                ["🔴 Выключить техрежим"],
                ["👑 Админ-панель"],
            ]

        if text == "🔴 Выключить техрежим":
            with self._conn() as c:
                c.execute(
                    "INSERT INTO settings(key,value) VALUES('maintenance_mode',?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    ("0",)
                )
            self._log(uid, "maintenance", None, "off")
            return True, (
                "🟢 ТЕХНИЧЕСКИЙ РЕЖИМ\n\n"
                "🟢 Технический режим выключен.\n\n"
                "🏙️ BANDIT CITY снова доступен игрокам."
            ), [
                ["🟢 Включить техрежим"],
                ["👑 Админ-панель"],
            ]


        st = self.state.get(uid)
        if st in ("grant_role", "change_role", "revoke_role"):
            if self.role(uid) < Role.OWNER:
                self.state.pop(uid, None)
                return True, "⛔ Доступ только владельцу.", [["🏙️ Главное меню"]]
            try:
                parts = text.split()
                target = int(parts[0])
                if st == "revoke_role":
                    result = self.roles.revoke(uid, target)
                else:
                    if len(parts) != 2 or parts[1].lower() not in ("admin", "moderator", "player"):
                        raise ValueError
                    role_map = {"admin": Role.ADMIN, "moderator": Role.MODERATOR, "player": Role.PLAYER}
                    result = self.roles.set_role(uid, target, role_map[parts[1].lower()])
                self.state.pop(uid, None)
                ok, message = result
                return True, message, [["👑 Центр владельца"]]
            except (ValueError, IndexError):
                return True, "❌ Формат: VK_ID admin|moderator|player", [["👑 Центр владельца"]]

        st = self.state.get(uid)
        if st in ("cash", "bank"):
            if text.lower() == "отмена":
                self.state.pop(uid, None)
                return True, "Операция отменена.", [["👑 Админ-панель"]]
            try:
                target, amount = map(int, text.split()[:2])
            except ValueError:
                return True, "❌ Формат: VK_ID СУММА", [["👑 Админ-панель"]]
            ok = self._set_cash(target, amount) if st == "cash" else self._set_bank(target, amount)
            self._log(uid, "set_cash" if st == "cash" else "set_bank", target, amount)
            self.state.pop(uid, None)
            return True, "✅ Изменено." if ok else "❌ Игрок не найден.", [["👑 Админ-панель"]]

        if text == "🧾 Журнал":
            return True, self._logs(), [["👑 Админ-панель"]]
        if text == "🎨 Внешность":
            if self.role(uid) < Role.ADMIN:
                return True, "⛔ Доступ только ADMIN.", [["🏙️ Главное меню"]]
            return True, "🎨 ВНЕШНОСТЬ\n\nВыбери действие.", [["🔎 Посмотреть внешность", "✏️ Изменить внешность"], ["👑 Админ-панель"]]
        if text == "🔎 Посмотреть внешность":
            self.state[uid] = "appearance_lookup"
            return True, "🔎 Введи VK ID игрока.", [["❌ Отмена"], ["🎨 Внешность"]]
        if text == "✏️ Изменить внешность":
            self.state[uid] = "appearance_set"
            return True, "✏️ Формат: VK_ID SLOT VALUE", [["❌ Отмена"], ["🎨 Внешность"]]
        if text == "🎪 Ивенты":
            from catalog import EVENTS, active_events
            active = active_events()
            body = ["🎪 УПРАВЛЕНИЕ ИВЕНТАМИ", ""]
            for key, event in EVENTS.items():
                body.append("{} {} — {}".format("🟢" if key in active else "⚪", event["title"], key))
                body.append("   {} → {}".format(event.get("start_at", "∞"), event.get("end_at", "∞")))
                body.append("   🎁 {}".format(", ".join(event["drops"])))
            return True, "\n".join(body), [["👑 Админ-панель"]]

        if text.startswith("/apcars "):
            try: target=int(text.split()[1])
            except (ValueError, IndexError): return True, "❌ Формат: /apcars VK_ID", [["👑 Админ-панель"]]
            rows=self._cars(target)
            if rows is None: return True, "❌ Игрок не найден.", [["👑 Админ-панель"]]
            body=["🚗 МАШИНЫ VK {}".format(target)]
            body += ["#{} • {} • {} • ⚡{} • ${}".format(r["id"],r["model"],r["category"],r["speed"],format(r["price"],",")) for r in rows]
            return True, "\n".join(body).replace(",", " "), [["👑 Админ-панель"]]
        if text.startswith("/acardel "):
            try: target,car_id=map(int,text.split()[1:3])
            except (ValueError, IndexError): return True, "❌ Формат: /acardel VK_ID CAR_ID", [["👑 Админ-панель"]]
            with self._conn() as c: cur=c.execute("DELETE FROM cars WHERE id=? AND user_id=(SELECT id FROM users WHERE vk_id=?)",(car_id,target))
            self._log(uid,"car_delete",target,car_id)
            return True, "✅ Машина удалена." if cur.rowcount else "❌ Машина не найдена.", [["👑 Админ-панель"]]
        if text.startswith("/apitems "):
            try: target=int(text.split()[1])
            except (ValueError, IndexError): return True, "❌ Формат: /apitems VK_ID", [["👑 Админ-панель"]]
            rows=self._items(target)
            if rows is None: return True, "❌ Игрок не найден.", [["👑 Админ-панель"]]
            body=["🎒 ВЕЩИ VK {}".format(target)]
            body += ["#{} • {} • ${}".format(r["id"],r["name"],format(r["price"],",")) for r in rows]
            return True, "\n".join(body).replace(",", " "), [["👑 Админ-панель"]]
        if text.startswith("/aitemdel "):
            try: target,item_id=map(int,text.split()[1:3])
            except (ValueError, IndexError): return True, "❌ Формат: /aitemdel VK_ID ITEM_ID", [["👑 Админ-панель"]]
            with self._conn() as c: cur=c.execute("DELETE FROM items WHERE id=? AND user_id=(SELECT id FROM users WHERE vk_id=?)",(item_id,target))
            self._log(uid,"item_delete",target,item_id)
            return True, "✅ Вещь удалена." if cur.rowcount else "❌ Вещь не найдена.", [["👑 Админ-панель"]]
        if text.startswith("/aappearance "):
            try: target=int(text.split()[1])
            except (ValueError, IndexError): return True, "❌ Формат: /aappearance VK_ID", [["👑 Админ-панель"]]
            row=self._find(target)
            if not row: return True, "❌ Игрок не найден.", [["👑 Админ-панель"]]
            a=self.db.appearance(row["id"])
            msg="🎨 ВНЕШНОСТЬ VK {}\n\n💇 {}\n👕 {}\n👖 {}\n🥾 {}\n🧢 {}\n💍 {}\n🌆 {}".format(target,a["hair"],a["clothes"],a["pants"],a["shoes"],a["head"],a["accessory"],a["background"])
            return True,msg,[["👑 Админ-панель"]]
        if text == "/adminlogs":
            return True, self._logs(), [["👑 Админ-панель"]]
        if text.startswith("/aplayer "):
            try:
                target = int(text.split()[1])
            except (ValueError, IndexError):
                return True, "❌ VK_ID", [["👑 Админ-панель"]]
            r = self._find(target)
            if not r:
                return True, "❌ Игрок не найден.", [["👑 Админ-панель"]]
            msg = (f"👤 ИГРОК {target}\n\n💵 {r['balance']:,}\n🏦 {r['bank']:,}\n⭐ Уровень {r['level']}\n✨ XP {r['xp']}\n⛔ Бан: {'да' if r['banned'] else 'нет'}").replace(",", " ")
            return True, msg, [["👑 Админ-панель"]]
        if text.startswith("/acash ") or text.startswith("/abank "):
            try:
                target, amount = map(int, text.split()[1:3])
            except ValueError:
                return True, "❌ Формат: /acash VK_ID SUM", [["👑 Админ-панель"]]
            cash = text.startswith("/acash")
            ok = self._set_cash(target, amount) if cash else self._set_bank(target, amount)
            self._log(uid, "set_cash" if cash else "set_bank", target, amount)
            return True, "✅ Готово." if ok else "❌ Игрок не найден.", [["👑 Админ-панель"]]
        if text.startswith("/axp ") or text.startswith("/alevel "):
            try:
                target, amount = map(int, text.split()[1:3])
            except ValueError:
                return True, "❌ Формат неверный.", [["👑 Админ-панель"]]
            xp = text.startswith("/axp")
            ok = self._set_xp(target, amount) if xp else self._set_level(target, amount)
            self._log(uid, "set_xp" if xp else "set_level", target, amount)
            return True, "✅ Готово." if ok else "❌ Игрок не найден.", [["👑 Админ-панель"]]
        if text.startswith("/astock "):
            try:
                target, amount = map(int, text.split()[1:3])
            except ValueError:
                return True, "❌ Формат: /astock VK_ID SUM", [["👑 Админ-панель"]]
            ok = self._set_stock(target, amount)
            self._log(uid, "set_stock", target, amount)
            return True, "✅ Склад изменён." if ok else "❌ Игрок или бизнес не найден.", [["👑 Админ-панель"]]
        if text.startswith("/aban ") or text.startswith("/aunban "):
            try:
                target = int(text.split()[1])
            except ValueError:
                return True, "❌ VK_ID", [["👑 Админ-панель"]]
            ban = text.startswith("/aban ")
            ok = self._toggle_ban(target, ban)
            self._log(uid, "ban" if ban else "unban", target)
            return True, ("⛔ Заблокирован." if ban else "✅ Разблокирован.") if ok else "❌ Игрок не найден.", [["👑 Админ-панель"]]
        if text.startswith("/promolist"):
            with self._conn() as c:
                rows = c.execute("SELECT code,title,reward_cash,reward_xp,used_count,max_uses,active FROM promo_codes ORDER BY code").fetchall()
            body = ["🎟 ПРОМОКОДЫ"] + [f"{r['code']} • ${r['reward_cash']:,} • +{r['reward_xp']} XP • {r['used_count']}/{r['max_uses'] or '∞'} • {'ON' if r['active'] else 'OFF'}".replace(",", " ") for r in rows]
            return True, "\n".join(body), [["👑 Админ-панель"]]
        if text.startswith("/promodel "):
            code = text.split()[1].upper()
            with self._conn() as c:
                cur = c.execute("UPDATE promo_codes SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE code=?", (code,))
            return True, "✅ Переключено." if cur.rowcount else "❌ Код не найден.", [["👑 Админ-панель"]]
        if text.startswith("/promoadd "):
            try:
                parts = text[10:].split("|")
                if len(parts) not in (5, 7):
                    raise ValueError
                code, title, cash, xp, max_uses = parts[:5]
                item = parts[5].strip() if len(parts) == 7 else None
                slot = parts[6].strip() if len(parts) == 7 else None
                with self._conn() as c:
                    c.execute(
                        "INSERT OR REPLACE INTO promo_codes(code,title,reward_cash,reward_xp,reward_item,reward_slot,max_uses,used_count,active) VALUES(?,?,?,?,?,?,?,0,1)",
                        (code.strip().upper(), title.strip(), int(cash), int(xp), item or None, slot or None, int(max_uses))
                    )
                self._log(uid, "promo_add", None, code.strip().upper())
                return True, "✅ Промокод создан.", [["👑 Админ-панель"]]
            except Exception:
                return True, "❌ Формат: CODE|TITLE|CASH|XP|MAX_USES[|ITEM|SLOT]", [["👑 Админ-панель"]]
        if text.startswith("/asetappearance "):
            try:
                parts=text.split(maxsplit=3)
                if len(parts) < 4:
                    raise ValueError
                target=int(parts[1]); slot=parts[2].strip(); value=parts[3].strip()
                if slot not in {"hair","clothes","pants","shoes","head","accessory","background"} or not value:
                    raise ValueError
            except (ValueError, IndexError):
                return True, "❌ Формат: /asetappearance VK_ID SLOT VALUE", [["👑 Админ-панель"]]
            row=self._find(target)
            if not row:
                return True, "❌ Игрок не найден.", [["👑 Админ-панель"]]
            self.db.set_appearance(row["id"], **{slot:value})
            self._log(uid,"appearance_set",target,f"{slot}={value}")
            return True, "✅ Внешность изменена.", [["👑 Админ-панель"]]

        if text.startswith("/maintenance "):
            value = text.split()[1].lower()
            if value not in ("on", "off"):
                return True, "❌ on/off", [["👑 Админ-панель"]]
            with self._conn() as c:
                c.execute("INSERT INTO settings(key,value) VALUES('maintenance_mode',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", ("1" if value == "on" else "0",))
            self._log(uid, "maintenance", None, value)
            return True, "🔧 Техрежим включён." if value == "on" else "🟢 Техрежим выключен.", [["👑 Админ-панель"]]
        return False, "", []
