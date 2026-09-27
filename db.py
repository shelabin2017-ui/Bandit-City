import secrets
import sqlite3
import string
import time


class Database:
    def __init__(self, path):
        self.path = path
        self.init()

    def connect(self):
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        return c

    def init(self):
        with self.connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vk_id INTEGER UNIQUE NOT NULL,
                city TEXT NOT NULL DEFAULT 'Los Santos',
                balance INTEGER NOT NULL DEFAULT 100000,
                bank INTEGER NOT NULL DEFAULT 0,
                level INTEGER NOT NULL DEFAULT 1,
                xp INTEGER NOT NULL DEFAULT 0,
                ref_code TEXT UNIQUE,
                referred_by INTEGER,
                referrals INTEGER NOT NULL DEFAULT 0,
                banned INTEGER NOT NULL DEFAULT 0,
                onboarding_done INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS jobs(
                user_id INTEGER NOT NULL,
                job TEXT NOT NULL,
                last_work INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(user_id,job)
            );
            CREATE TABLE IF NOT EXISTS businesses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                type TEXT NOT NULL,
                level INTEGER NOT NULL DEFAULT 1,
                stock INTEGER NOT NULL DEFAULT 0,
                balance INTEGER NOT NULL DEFAULT 0,
                last_tick INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cars(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                model TEXT NOT NULL,
                category TEXT NOT NULL,
                speed INTEGER NOT NULL,
                price INTEGER NOT NULL,
                bought_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                bought_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS attacks(
                attacker_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                mode TEXT NOT NULL,
                last_attack INTEGER NOT NULL,
                PRIMARY KEY(attacker_id,target_id,mode)
            );
            CREATE TABLE IF NOT EXISTS transactions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user INTEGER,
                to_user INTEGER,
                amount INTEGER NOT NULL,
                type TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS daily_rewards(
                user_id INTEGER PRIMARY KEY,
                last_claim INTEGER NOT NULL DEFAULT 0,
                streak INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS achievements(
                user_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                PRIMARY KEY(user_id, code)
            );
            CREATE TABLE IF NOT EXISTS user_appearance(
                user_id INTEGER PRIMARY KEY,
                hair TEXT NOT NULL DEFAULT 'default',
                clothes TEXT NOT NULL DEFAULT 'default',
                pants TEXT NOT NULL DEFAULT 'default',
                shoes TEXT NOT NULL DEFAULT 'default',
                head TEXT NOT NULL DEFAULT 'default',
                accessory TEXT NOT NULL DEFAULT 'none',
                background TEXT NOT NULL DEFAULT 'city',
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS v5_wardrobe(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                bought_at INTEGER NOT NULL,
                UNIQUE(user_id, category, name)
            );
            CREATE TABLE IF NOT EXISTS v5_weapons(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                bought_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS v5_purchases(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                bought_at INTEGER NOT NULL
            );
            """)
            self.add_column(c, "users", "ref_code", "TEXT")
            self.add_column(c, "users", "referred_by", "INTEGER")
            self.add_column(c, "users", "referrals", "INTEGER NOT NULL DEFAULT 0")
            self.add_column(c, "users", "banned", "INTEGER NOT NULL DEFAULT 0")
            self.add_column(c, "users", "onboarding_done", "INTEGER NOT NULL DEFAULT 0")
            for row in c.execute("SELECT id FROM users WHERE ref_code IS NULL OR ref_code=''").fetchall():
                c.execute("UPDATE users SET ref_code=? WHERE id=?", (self.new_ref(), row["id"]))

    @staticmethod
    def add_column(c, table, column, definition):
        cols = {r[1] for r in c.execute(f"PRAGMA table_info({table})")}
        if column not in cols:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    @staticmethod
    def new_ref():
        return "R" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))

    def appearance(self, user_id):
        with self.connect() as c:
            row=c.execute("SELECT * FROM user_appearance WHERE user_id=?", (user_id,)).fetchone()
            if row:
                return row
            now=int(time.time())
            c.execute("INSERT INTO user_appearance(user_id,hair,clothes,pants,shoes,head,accessory,background,updated_at) VALUES(?,?,?,?,?,?,?,?,?)", (user_id,"default","default","default","default","default","none","city",now))
            return c.execute("SELECT * FROM user_appearance WHERE user_id=?", (user_id,)).fetchone()

    def set_appearance(self, user_id, **values):
        allowed={"hair","clothes","pants","shoes","head","accessory","background"}
        values={k:v for k,v in values.items() if k in allowed}
        self.appearance(user_id)
        if not values:
            return
        values["updated_at"]=int(time.time())
        fields=", ".join(k+"=?" for k in values)
        params=list(values.values())+[user_id]
        with self.connect() as c:
            c.execute("UPDATE user_appearance SET "+fields+" WHERE user_id=?", params)

    def get_or_create_user(self, vk_id):
        with self.connect() as c:
            row = c.execute("SELECT * FROM users WHERE vk_id=?", (vk_id,)).fetchone()
            if row:
                return row
            c.execute(
                "INSERT INTO users(vk_id,ref_code,created_at) VALUES(?,?,?)",
                (vk_id, self.new_ref(), int(time.time()))
            )
            return c.execute("SELECT * FROM users WHERE vk_id=?", (vk_id,)).fetchone()

    def needs_onboarding(self, user_id):
        with self.connect() as c:
            r = c.execute("SELECT onboarding_done FROM users WHERE id=?", (user_id,)).fetchone()
            return bool(r and not r["onboarding_done"])

    def complete_onboarding(self, user_id):
        with self.connect() as c:
            c.execute("UPDATE users SET onboarding_done=1 WHERE id=?", (user_id,))

    def is_banned(self, vk_id):
        with self.connect() as c:
            r = c.execute("SELECT banned FROM users WHERE vk_id=?", (vk_id,)).fetchone()
            return bool(r and r["banned"])

    def user(self, user_id):
        with self.connect() as c:
            return c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

    def add_money(self, user_id, delta):
        with self.connect() as c:
            c.execute("UPDATE users SET balance=balance+? WHERE id=?", (delta, user_id))

    def add_money_vk(self, vk_id, delta):
        with self.connect() as c:
            c.execute("UPDATE users SET balance=balance+? WHERE vk_id=?", (delta, vk_id))

    def xp(self, user_id, amount):
        with self.connect() as c:
            c.execute("UPDATE users SET xp=xp+? WHERE id=?", (amount, user_id))
            r = c.execute("SELECT xp FROM users WHERE id=?", (user_id,)).fetchone()
            c.execute("UPDATE users SET level=? WHERE id=?", (r["xp"] // 100 + 1, user_id))

    def job_last(self, user_id, job):
        with self.connect() as c:
            r = c.execute("SELECT last_work FROM jobs WHERE user_id=? AND job=?", (user_id, job)).fetchone()
            return r["last_work"] if r else 0

    def job_set(self, user_id, job):
        with self.connect() as c:
            c.execute(
                "INSERT INTO jobs(user_id,job,last_work) VALUES(?,?,?) "
                "ON CONFLICT(user_id,job) DO UPDATE SET last_work=excluded.last_work",
                (user_id, job, int(time.time()))
            )

    def tick_business(self, c, b):
        now = int(time.time())
        minutes = max(0, (now - b["last_tick"]) // 60)
        if minutes <= 0:
            return 0
        use = min(minutes, b["stock"])
        if use:
            income = use * 80_000
            c.execute(
                "UPDATE businesses SET stock=stock-?,balance=balance+?,last_tick=? WHERE id=?",
                (use, income, now, b["id"])
            )
            return income
        c.execute("UPDATE businesses SET last_tick=? WHERE id=?", (now, b["id"]))
        return 0

    def tick_all_businesses(self):
        with self.connect() as c:
            for b in c.execute("SELECT * FROM businesses").fetchall():
                self.tick_business(c, b)

    def business(self, user_id):
        with self.connect() as c:
            b = c.execute("SELECT * FROM businesses WHERE user_id=?", (user_id,)).fetchone()
            if not b:
                return None
            self.tick_business(c, b)
            return c.execute("SELECT * FROM businesses WHERE user_id=?", (user_id,)).fetchone()

    def buy_business(self, user_id):
        price = 100_000_000
        with self.connect() as c:
            u = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if c.execute("SELECT 1 FROM businesses WHERE user_id=?", (user_id,)).fetchone():
                return "❌ У тебя уже есть бизнес."
            if u["balance"] < price:
                return "❌ Недостаточно денег."
            c.execute("UPDATE users SET balance=balance-? WHERE id=?", (price, user_id))
            c.execute(
                "INSERT INTO businesses(user_id,type,last_tick) VALUES(?,?,?)",
                (user_id, "airport", int(time.time()))
            )
            return "🏭 Контрабандистский аэропорт куплен!"

    def refill(self, user_id, amount):
        if amount <= 0:
            return "❌ Количество должно быть положительным."
        with self.connect() as c:
            b = c.execute("SELECT * FROM businesses WHERE user_id=?", (user_id,)).fetchone()
            if not b:
                return "❌ Сначала купи бизнес."
            self.tick_business(c, b)
            b = c.execute("SELECT * FROM businesses WHERE user_id=?", (user_id,)).fetchone()
            free = 5_000_000 - b["stock"]
            amount = min(amount, free)
            price = amount * 40_000
            u = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if amount <= 0:
                return "❌ Склад заполнен."
            if u["balance"] < price:
                return "❌ Не хватает денег."
            c.execute("UPDATE users SET balance=balance-? WHERE id=?", (price, user_id))
            c.execute("UPDATE businesses SET stock=stock+? WHERE id=?", (amount, b["id"]))
            return f"📦 Загружено: {amount:,}\n💵 Стоимость: ${price:,}".replace(",", " ")

    def withdraw(self, user_id):
        with self.connect() as c:
            b = c.execute("SELECT * FROM businesses WHERE user_id=?", (user_id,)).fetchone()
            if not b:
                return "❌ Бизнеса нет."
            self.tick_business(c, b)
            b = c.execute("SELECT * FROM businesses WHERE user_id=?", (user_id,)).fetchone()
            if b["balance"] <= 0:
                return "💸 Касса пуста."
            amount = b["balance"]
            c.execute("UPDATE businesses SET balance=0 WHERE id=?", (b["id"],))
            c.execute("UPDATE users SET balance=balance+? WHERE id=?", (amount, user_id))
            c.execute(
                "INSERT INTO transactions(from_user,to_user,amount,type,created_at) VALUES(NULL,?,?,?,?)",
                (user_id, amount, "business_withdraw", int(time.time()))
            )
            return f"💰 Снято: ${amount:,}".replace(",", " ")

    def referral(self, user_id, code):
        with self.connect() as c:
            u = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if u["referred_by"]:
                return False
            r = c.execute("SELECT * FROM users WHERE ref_code=?", (code,)).fetchone()
            if not r or r["id"] == user_id:
                return False
            c.execute("UPDATE users SET referred_by=? WHERE id=?", (r["id"], user_id))
            c.execute("UPDATE users SET referrals=referrals+1,balance=balance+100000 WHERE id=?", (r["id"],))
            c.execute("UPDATE users SET balance=balance+50000 WHERE id=?", (user_id,))
            return True

    def transfer(self, user_id, target_vk, amount):
        if amount < 100:
            return "❌ Минимум $100."
        with self.connect() as c:
            a = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            b = c.execute("SELECT * FROM users WHERE vk_id=?", (target_vk,)).fetchone()
            if not b:
                return "❌ Игрок не найден."
            if a["id"] == b["id"]:
                return "❌ Нельзя переводить самому себе."
            if a["balance"] < amount:
                return "❌ Недостаточно денег."
            c.execute("UPDATE users SET balance=balance-? WHERE id=?", (amount, a["id"]))
            c.execute("UPDATE users SET balance=balance+? WHERE id=?", (amount, b["id"]))
            c.execute(
                "INSERT INTO transactions(from_user,to_user,amount,type,created_at) VALUES(?,?,?,?,?)",
                (a["id"], b["id"], amount, "transfer", int(time.time()))
            )
            return f"💸 Перевод {money(amount)} выполнен."

    def attack(self, user_id, target_vk, mode):
        cooldown = 1800
        with self.connect() as c:
            a = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            b = c.execute("SELECT * FROM users WHERE vk_id=?", (target_vk,)).fetchone()
            if not b:
                return "❌ Игрок не найден."
            if a["id"] == b["id"]:
                return "❌ Нельзя атаковать себя."
            if a["level"] < 2:
                return "❌ Нужен 2 уровень."
            old = c.execute(
                "SELECT last_attack FROM attacks WHERE attacker_id=? AND target_id=? AND mode=?",
                (a["id"], b["id"], mode)
            ).fetchone()
            now = int(time.time())
            if old and now - old["last_attack"] < cooldown:
                left = cooldown - (now - old["last_attack"])
                return f"⏳ Жди {left//60} мин. {left%60} сек."
            c.execute(
                "INSERT INTO attacks(attacker_id,target_id,mode,last_attack) VALUES(?,?,?,?) "
                "ON CONFLICT(attacker_id,target_id,mode) DO UPDATE SET last_attack=excluded.last_attack",
                (a["id"], b["id"], mode, now)
            )
            chance = 0.45 if mode == "scam" else 0.35
            if random.random() > chance:
                return "❌ Попытка провалилась."
            available = max(0, b["balance"])
            if available <= 0:
                return "❌ У цели нет наличных."
            stolen = min(available * random.randint(10,30)//100, 500_000)
            gain = stolen * 70 // 100
            c.execute("UPDATE users SET balance=balance-? WHERE id=?", (stolen, b["id"]))
            c.execute("UPDATE users SET balance=balance+? WHERE id=?", (gain, a["id"]))
            c.execute(
                "INSERT INTO transactions(from_user,to_user,amount,type,created_at) VALUES(?,?,?,?,?)",
                (b["id"], a["id"], gain, mode, now)
            )
            return f"🕶 УСПЕХ!\n🎯 VK {target_vk}\n💰 Добыча: {money(gain)}"

    def cars(self, user_id):
        with self.connect() as c:
            return c.execute("SELECT * FROM cars WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()

    def buy_car(self, user_id, model):
        cars = {
            "Clover":("common",10,1_000_000),"Elegy":("common",12,2_000_000),
            "Sultan":("sport",20,8_000_000),"Banshee":("sport",25,12_000_000),
            "Infernus":("super",40,50_000_000),"Turismo":("super",45,65_000_000),
            "Savanna":("lowrider",14,5_000_000),"Voodoo":("lowrider",16,6_000_000)
        }
        if model not in cars:
            return "❌ Такой машины нет."
        cat,speed,price = cars[model]
        with self.connect() as c:
            u = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if u["balance"] < price:
                return "❌ Недостаточно денег."
            c.execute("UPDATE users SET balance=balance-? WHERE id=?", (price,user_id))
            c.execute(
                "INSERT INTO cars(user_id,model,category,speed,price,bought_at) VALUES(?,?,?,?,?,?)",
                (user_id,model,cat,speed,price,int(time.time()))
            )
            return f"✅ {model} куплен за {money(price)}"

    def sell_car(self,user_id,car_id):
        with self.connect() as c:
            car=c.execute("SELECT * FROM cars WHERE id=? AND user_id=?",(car_id,user_id)).fetchone()
            if not car: return "❌ Машина не найдена."
            payout=car["price"]*70//100
            c.execute("DELETE FROM cars WHERE id=?",(car_id,))
            c.execute("UPDATE users SET balance=balance+? WHERE id=?",(payout,user_id))
            return f"🚘 Продано. Получено {money(payout)}"

    def items(self,user_id):
        with self.connect() as c:
            return c.execute("SELECT * FROM items WHERE user_id=? ORDER BY id DESC",(user_id,)).fetchall()

    def buy_item(self,user_id,name,price):
        with self.connect() as c:
            u=c.execute("SELECT * FROM users WHERE id=?",(user_id,)).fetchone()
            if u["balance"]<price: return "❌ Недостаточно денег."
            c.execute("UPDATE users SET balance=balance-? WHERE id=?",(price,user_id))
            c.execute("INSERT INTO items(user_id,name,price,bought_at) VALUES(?,?,?,?)",(user_id,name,price,int(time.time())))
            return f"✅ {name} куплен за {money(price)}"

    def sell_item(self,user_id,item_id):
        with self.connect() as c:
            item=c.execute("SELECT * FROM items WHERE id=? AND user_id=?",(item_id,user_id)).fetchone()
            if not item: return "❌ Вещь не найдена."
            payout=item["price"]*70//100
            c.execute("DELETE FROM items WHERE id=?",(item_id,))
            c.execute("UPDATE users SET balance=balance+? WHERE id=?",(payout,user_id))
            return f"📦 Продано. Получено {money(payout)}"

    def top(self):
        with self.connect() as c:
            rows=c.execute(
                "SELECT vk_id,balance,bank,level,referrals FROM users WHERE banned=0 "
                "ORDER BY balance+bank DESC LIMIT 10"
            ).fetchall()
        if not rows: return "🏆 Пока никого нет."
        return "🏆 ТОП ИГРОКОВ\n\n" + "\n".join(
            f"{i}. VK {r['vk_id']} — {money(r['balance']+r['bank'])} | ⭐ {r['level']}"
            for i,r in enumerate(rows,1)
        )

    def bank_deposit(self, user_id, amount):
        if amount <= 0:
            return "❌ Сумма должна быть положительной."
        with self.connect() as c:
            u = c.execute("SELECT balance FROM users WHERE id=?", (user_id,)).fetchone()
            if not u or u["balance"] < amount:
                return "❌ Недостаточно наличных."
            c.execute("UPDATE users SET balance=balance-?, bank=bank+? WHERE id=?", (amount, amount, user_id))
            return f"🏦 В банк внесено {money(amount)}."

    def bank_withdraw(self, user_id, amount):
        if amount <= 0:
            return "❌ Сумма должна быть положительной."
        with self.connect() as c:
            u = c.execute("SELECT bank FROM users WHERE id=?", (user_id,)).fetchone()
            if not u or u["bank"] < amount:
                return "❌ В банке недостаточно денег."
            c.execute("UPDATE users SET bank=bank-?, balance=balance+? WHERE id=?", (amount, amount, user_id))
            return f"🏦 Из банка снято {money(amount)}."

    def daily(self, user_id):
        now = int(time.time())
        with self.connect() as c:
            r = c.execute("SELECT * FROM daily_rewards WHERE user_id=?", (user_id,)).fetchone()
            if r and now - r["last_claim"] < 86400:
                left = 86400 - (now-r["last_claim"])
                return f"⏳ Ежедневный бонус уже получен. Осталось {left//3600} ч. {left%3600//60} мин."
            streak = (r["streak"] + 1) if r and now-r["last_claim"] <= 172800 else 1
            reward = min(50_000 + (streak-1)*10_000, 150_000)
            c.execute("INSERT INTO daily_rewards(user_id,last_claim,streak) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET last_claim=excluded.last_claim,streak=excluded.streak", (user_id, now, streak))
            c.execute("UPDATE users SET balance=balance+? WHERE id=?", (reward, user_id))
            return f"🎁 ЕЖЕДНЕВНЫЙ БОНУС\n💵 +{money(reward)}\n🔥 Серия: {streak}"

    def achievements(self, user_id):
        u = self.user(user_id)
        unlocked = []
        checks = [("first_work", u["xp"] >= 10, "💼 Первая работа"), ("level5", u["level"] >= 5, "⭐ Уровень 5"), ("rich", u["balance"]+u["bank"] >= 10_000_000, "💰 Капитал 10 млн"), ("ref5", u["referrals"] >= 5, "👥 5 рефералов")]
        with self.connect() as c:
            for code, ok, title in checks:
                if ok:
                    cur = c.execute("INSERT OR IGNORE INTO achievements(user_id,code,created_at) VALUES(?,?,?)", (user_id,code,int(time.time())))
                    if cur.rowcount:
                        unlocked.append(title)
            rows = c.execute("SELECT code FROM achievements WHERE user_id=? ORDER BY created_at", (user_id,)).fetchall()
        names = {code:title for code,_,title in checks}
        body = ["🏆 ДОСТИЖЕНИЯ", ""]
        for r in rows:
            body.append("✅ " + names.get(r["code"], r["code"]))
        if unlocked:
            body += ["", "🎉 Новые достижения:", *["+ " + x for x in unlocked]]
        if len(rows) == 0:
            body.append("Пока нет открытых достижений.")
        return "\n".join(body)

    def admin_stats(self):
        with self.connect() as c:
            users=c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
            cars=c.execute("SELECT COUNT(*) n FROM cars").fetchone()["n"]
            items=c.execute("SELECT COUNT(*) n FROM items").fetchone()["n"]
            businesses=c.execute("SELECT COUNT(*) n FROM businesses").fetchone()["n"]
            economy=c.execute("SELECT COALESCE(SUM(balance+bank),0) n FROM users").fetchone()["n"]
        return (
            "📊 АДМИН-СТАТИСТИКА\n\n"
            f"👥 Игроков: {users}\n🚗 Машин: {cars}\n🎒 Вещей: {items}\n"
            f"🏢 Бизнесов: {businesses}\n💰 Денег: {money(economy)}"
        )

    def admin_money(self,vk_id,delta):
        with self.connect() as c:
            c.execute("UPDATE users SET balance=balance+? WHERE vk_id=?",(delta,vk_id))

    def admin_level(self,vk_id,level):
        with self.connect() as c:
            c.execute("UPDATE users SET level=? WHERE vk_id=?",(level,vk_id))

    def admin_ban(self,vk_id,value):
        with self.connect() as c:
            c.execute("UPDATE users SET banned=? WHERE vk_id=?",(int(value),vk_id))

    def admin_stock(self,vk_id,stock):
        stock=max(0,min(5_000_000,stock))
        with self.connect() as c:
            u=c.execute("SELECT id FROM users WHERE vk_id=?",(vk_id,)).fetchone()
            if not u: return False
            b=c.execute("SELECT id FROM businesses WHERE user_id=?",(u["id"],)).fetchone()
            if not b: return False
            c.execute("UPDATE businesses SET stock=? WHERE id=?",(stock,b["id"]))
            return True


def money(n):
    return f"${int(n):,}".replace(",", " ")
