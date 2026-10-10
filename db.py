import random
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
            CREATE TABLE IF NOT EXISTS promo_codes(
                code TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                reward_cash INTEGER NOT NULL DEFAULT 0,
                reward_xp INTEGER NOT NULL DEFAULT 0,
                reward_item TEXT,
                reward_slot TEXT,
                max_uses INTEGER NOT NULL DEFAULT 0,
                used_count INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS promo_redemptions(
                user_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                redeemed_at INTEGER NOT NULL,
                PRIMARY KEY(user_id, code)
            );
            CREATE TABLE IF NOT EXISTS mission_progress(
                user_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                claimed INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY(user_id, code)
            );
            CREATE TABLE IF NOT EXISTS sms_task_progress(
                user_id INTEGER NOT NULL,
                task_code TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                claimed INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY(user_id, task_code)
            );
            CREATE TABLE IF NOT EXISTS sms_messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sender TEXT NOT NULL,
                text TEXT NOT NULL,
                task_code TEXT,
                reward_cash INTEGER NOT NULL DEFAULT 0,
                reward_xp INTEGER NOT NULL DEFAULT 0,
                read INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS story_progress(
                user_id INTEGER PRIMARY KEY,
                chapter INTEGER NOT NULL DEFAULT 1,
                step INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tutorial_progress(
                user_id INTEGER PRIMARY KEY,
                step INTEGER NOT NULL DEFAULT 0,
                completed INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS player_status(
                user_id INTEGER PRIMARY KEY,
                heat INTEGER NOT NULL DEFAULT 0,
                reputation INTEGER NOT NULL DEFAULT 0,
                energy INTEGER NOT NULL DEFAULT 100,
                last_update INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS city_events(
                code TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                reward_cash INTEGER NOT NULL DEFAULT 0,
                reward_xp INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS casino_stats(
                user_id INTEGER PRIMARY KEY,
                plays INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                wagered INTEGER NOT NULL DEFAULT 0,
                profit INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS phone_contacts(
                user_id INTEGER NOT NULL,
                contact_id INTEGER NOT NULL,
                nickname TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                PRIMARY KEY(user_id, contact_id)
            );
            CREATE TABLE IF NOT EXISTS event_participation(
                user_id INTEGER NOT NULL,
                event_code TEXT NOT NULL,
                participated_at INTEGER NOT NULL,
                completed INTEGER NOT NULL DEFAULT 1,
                reward_claimed INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(user_id, event_code)
            );
            CREATE TABLE IF NOT EXISTS npc_state(
                user_id INTEGER NOT NULL,
                npc_code TEXT NOT NULL,
                value INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY(user_id, npc_code)
            );
            CREATE TABLE IF NOT EXISTS npc_cooldowns(
                user_id INTEGER NOT NULL,
                npc_code TEXT NOT NULL,
                action_code TEXT NOT NULL,
                ready_at INTEGER NOT NULL,
                PRIMARY KEY(user_id, npc_code, action_code)
            );
            """)
            self.add_column(c, "users", "ref_code", "TEXT")
            self.add_column(c, "users", "referred_by", "INTEGER")
            self.add_column(c, "users", "referrals", "INTEGER NOT NULL DEFAULT 0")
            self.add_column(c, "users", "banned", "INTEGER NOT NULL DEFAULT 0")
            self.add_column(c, "users", "onboarding_done", "INTEGER NOT NULL DEFAULT 0")
            self.add_column(c, "users", "nickname", "TEXT")
            self.add_column(c, "user_appearance", "pants", "TEXT NOT NULL DEFAULT 'default'")
            self.add_column(c, "user_appearance", "shoes", "TEXT NOT NULL DEFAULT 'default'")
            self.add_column(c, "user_appearance", "head", "TEXT NOT NULL DEFAULT 'default'")
            for row in c.execute("SELECT id FROM users WHERE ref_code IS NULL OR ref_code=''").fetchall():
                c.execute("UPDATE users SET ref_code=? WHERE id=?", (self.new_ref(), row["id"]))

            # Автоматические ники для уже существующих игроков.
            for row in c.execute("SELECT id FROM users WHERE nickname IS NULL OR TRIM(nickname)=''").fetchall():
                nickname = f"Игрок{row['id']}"
                c.execute("UPDATE users SET nickname=? WHERE id=?", (nickname, row["id"]))

            # Уникальные игровые ники.
            c.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_nickname "
                "ON users(nickname)"
            )

    @staticmethod
    def add_column(c, table, column, definition):
        cols = {r[1] for r in c.execute(f"PRAGMA table_info({table})")}
        if column not in cols:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    @staticmethod
    def new_ref():
        return "R" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))

    def event_participation(self, user_id, event_code):
        with self.connect() as c:
            row = c.execute(
                "SELECT * FROM event_participation WHERE user_id=? AND event_code=?",
                (int(user_id), str(event_code))
            ).fetchone()
            if row:
                return False, row
            now = int(time.time())
            c.execute(
                "INSERT INTO event_participation(user_id,event_code,participated_at,completed,reward_claimed) VALUES(?,?,?,?,?)",
                (int(user_id), str(event_code), now, 1, 0)
            )
            row = c.execute(
                "SELECT * FROM event_participation WHERE user_id=? AND event_code=?",
                (int(user_id), str(event_code))
            ).fetchone()
            return True, row

    def event_history(self, user_id):
        with self.connect() as c:
            return c.execute(
                "SELECT event_code,participated_at,completed,reward_claimed "
                "FROM event_participation WHERE user_id=? ORDER BY participated_at",
                (int(user_id),)
            ).fetchall()

    def event_reward_claimed(self, user_id, event_code):
        with self.connect() as c:
            c.execute(
                "UPDATE event_participation SET reward_claimed=1 "
                "WHERE user_id=? AND event_code=?",
                (int(user_id), str(event_code))
            )

    def sms_task_complete(self,user_id,task_code):
        with self.connect() as c:
            c.execute(
                "INSERT INTO sms_task_progress(user_id,task_code,completed,claimed,updated_at) VALUES(?,?,?,?,?) "
                "ON CONFLICT(user_id,task_code) DO UPDATE SET completed=1,updated_at=excluded.updated_at",
                (int(user_id),str(task_code),1,0,int(time.time()))
            )

    def sms_task_rows(self,user_id,codes):
        if not codes:
            return {}
        with self.connect() as c:
            rows=c.execute(
                "SELECT task_code,completed,claimed FROM sms_task_progress WHERE user_id=? AND task_code IN (%s)"
                % ",".join("?" for _ in codes), [int(user_id),*codes]
            ).fetchall()
        return {r["task_code"]:dict(r) for r in rows}

    def sms_task_claim(self,user_id,task_code,reward_cash,reward_xp):
        with self.connect() as c:
            row=c.execute("SELECT completed,claimed FROM sms_task_progress WHERE user_id=? AND task_code=?",(int(user_id),str(task_code))).fetchone()
            if not row or not row["completed"]:
                return False,"⏳ Задание ещё не выполнено."
            if row["claimed"]:
                return False,"❌ Награда уже получена."
            now=int(time.time())
            c.execute("UPDATE sms_task_progress SET claimed=1,updated_at=? WHERE user_id=? AND task_code=?",(now,int(user_id),str(task_code)))
            c.execute("UPDATE users SET balance=balance+?,xp=xp+? WHERE id=?",(int(reward_cash),int(reward_xp),int(user_id)))
            xp=c.execute("SELECT xp FROM users WHERE id=?",(int(user_id),)).fetchone()["xp"]
            c.execute("UPDATE users SET level=? WHERE id=?",(xp//100+1,int(user_id)))
        return True,f"🎉 ЗАДАНИЕ ВЫПОЛНЕНО\n\n💵 +{money(reward_cash)}\n✨ +{reward_xp} XP"
    def sms_list(self,user_id,limit=20):
        with self.connect() as c:
            return c.execute("SELECT * FROM sms_messages WHERE user_id=? ORDER BY id DESC LIMIT ?",(user_id,int(limit))).fetchall()

    def sms_add(self,user_id,sender,text,task_code=None,reward_cash=0,reward_xp=0):
        with self.connect() as c:
            c.execute("INSERT INTO sms_messages(user_id,sender,text,task_code,reward_cash,reward_xp,created_at) VALUES(?,?,?,?,?,?,?)",
                      (user_id,sender,text,task_code,int(reward_cash),int(reward_xp),int(time.time())))

    def sms_read(self,user_id,message_id):
        with self.connect() as c:
            c.execute("UPDATE sms_messages SET read=1 WHERE id=? AND user_id=?",(int(message_id),user_id))

    def story(self,user_id):
        with self.connect() as c:
            r=c.execute("SELECT * FROM story_progress WHERE user_id=?",(user_id,)).fetchone()
            if r: return r
            c.execute("INSERT INTO story_progress(user_id,chapter,step,updated_at) VALUES(?,?,?,?)",(user_id,1,0,int(time.time())))
            return c.execute("SELECT * FROM story_progress WHERE user_id=?",(user_id,)).fetchone()

    def story_set(self,user_id,chapter,step):
        with self.connect() as c:
            c.execute("INSERT INTO story_progress(user_id,chapter,step,updated_at) VALUES(?,?,?,?) "
                      "ON CONFLICT(user_id) DO UPDATE SET chapter=excluded.chapter,step=excluded.step,updated_at=excluded.updated_at",
                      (user_id,int(chapter),int(step),int(time.time())))

    def tutorial(self,user_id):
        with self.connect() as c:
            r=c.execute("SELECT * FROM tutorial_progress WHERE user_id=?",(user_id,)).fetchone()
            if r: return r
            c.execute("INSERT INTO tutorial_progress(user_id,step,completed,updated_at) VALUES(?,?,?,?)",(user_id,0,0,int(time.time())))
            return c.execute("SELECT * FROM tutorial_progress WHERE user_id=?",(user_id,)).fetchone()

    def tutorial_set(self,user_id,step,completed=False):
        with self.connect() as c:
            c.execute("INSERT INTO tutorial_progress(user_id,step,completed,updated_at) VALUES(?,?,?,?) "
                      "ON CONFLICT(user_id) DO UPDATE SET step=excluded.step,completed=excluded.completed,updated_at=excluded.updated_at",
                      (user_id,int(step),1 if completed else 0,int(time.time())))

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

    def seed_promos(self):
        promos=[
            ("NIGHTFALL-2026","NIGHTFALL • Founder Drop",250000,500,"🖤 Shadow Jacket","clothes",0),
            ("LOS-SANTOS-7","LOS SANTOS 7 • Neon Drop",150000,300,"🌌 Neon Shades","accessory",0),
            ("BANDIT-PRIME","BANDIT PRIME • Private Drop",500000,1000,"👑 Prime Hair","hair",0),
        ]
        with self.connect() as c:
            for p in promos:
                c.execute(
                    "INSERT OR IGNORE INTO promo_codes(code,title,reward_cash,reward_xp,reward_item,reward_slot,max_uses) VALUES(?,?,?,?,?,?,?)",
                    p
                )

    def redeem_promo(self, user_id, code):
        code=code.strip().upper()
        self.seed_promos()
        with self.connect() as c:
            promo=c.execute("SELECT * FROM promo_codes WHERE code=? AND active=1",(code,)).fetchone()
            if not promo:
                return False,"❌ Промокод не найден или уже отключён."
            if promo["max_uses"] and promo["used_count"]>=promo["max_uses"]:
                return False,"❌ Лимит промокода исчерпан."
            if c.execute("SELECT 1 FROM promo_redemptions WHERE user_id=? AND code=?",(user_id,code)).fetchone():
                return False,"❌ Ты уже использовал этот промокод."
            c.execute("INSERT INTO promo_redemptions(user_id,code,redeemed_at) VALUES(?,?,?)",(user_id,code,int(time.time())))
            if promo["reward_cash"]:
                c.execute("UPDATE users SET balance=balance+? WHERE id=?",(promo["reward_cash"],user_id))
            if promo["reward_xp"]:
                c.execute("UPDATE users SET xp=xp+? WHERE id=?",(promo["reward_xp"],user_id))
                xp=c.execute("SELECT xp FROM users WHERE id=?",(user_id,)).fetchone()["xp"]
                c.execute("UPDATE users SET level=? WHERE id=?",(xp//100+1,user_id))
            if promo["reward_item"]:
                c.execute(
                    "INSERT OR IGNORE INTO v5_wardrobe(user_id,category,name,price,bought_at) VALUES(?,?,?,?,?)",
                    (user_id,"🎟 PROMO",promo["reward_item"],0,int(time.time()))
                )
                now=int(time.time())
                c.execute(
                    "INSERT OR IGNORE INTO user_appearance(user_id,hair,clothes,pants,shoes,head,accessory,background,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (user_id,"default","default","default","default","default","none","city",now)
                )
                slot=promo["reward_slot"]
                if slot in {"hair","clothes","pants","shoes","head","accessory"}:
                    c.execute("UPDATE user_appearance SET "+slot+"=?, updated_at=? WHERE user_id=?",
                              (promo["reward_item"],now,user_id))
            c.execute("UPDATE promo_codes SET used_count=used_count+1 WHERE code=?",(code,))
            cash=f"${promo['reward_cash']:,}".replace(","," ")
            return True,("🎟 ПРОМОКОД АКТИВИРОВАН\n\n" +
                f"✨ {promo['title']}\n💵 +{cash}\n⭐ +{promo['reward_xp']} XP\n" +
                f"🎁 {promo['reward_item'] or 'Эксклюзивный бонус'}")

    def phone_contacts(self,user_id):
        with self.connect() as c:
            return c.execute("SELECT * FROM phone_contacts WHERE user_id=? ORDER BY nickname",(user_id,)).fetchall()

    def phone_add(self,user_id,contact_id,nickname):
        with self.connect() as c:
            owner = c.execute("SELECT vk_id FROM users WHERE id=?", (int(user_id),)).fetchone()
            if owner and int(contact_id) == int(owner["vk_id"]):
                return False,"❌ Нельзя добавить самого себя."
            if not str(nickname or "").strip():
                target = c.execute("SELECT nickname FROM users WHERE vk_id=?", (int(contact_id),)).fetchone()
                nickname = target["nickname"] if target else None
            if not str(nickname or "").strip():
                return False,"❌ У контакта нет игрового ника."
            c.execute("INSERT OR REPLACE INTO phone_contacts(user_id,contact_id,nickname,created_at) VALUES(?,?,?,?)",
                      (int(user_id),int(contact_id),str(nickname).strip(),int(time.time())))
        return True,"📱 Контакт добавлен."

    def phone_remove(self,user_id,contact_id):
        with self.connect() as c:
            cur=c.execute("DELETE FROM phone_contacts WHERE user_id=? AND contact_id=?",(user_id,contact_id))
        return bool(cur.rowcount)

    def npc_value(self,user_id,npc_code):
        with self.connect() as c:
            r=c.execute("SELECT value FROM npc_state WHERE user_id=? AND npc_code=?",(user_id,npc_code)).fetchone()
        return int(r["value"]) if r else 0

    def npc_set(self,user_id,npc_code,value):
        with self.connect() as c:
            c.execute("INSERT INTO npc_state(user_id,npc_code,value,updated_at) VALUES(?,?,?,?) "
                      "ON CONFLICT(user_id,npc_code) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                      (user_id,npc_code,int(value),int(time.time())))

    def npc_cooldown_remaining(self, user_id, npc_code, action_code):
        with self.connect() as c:
            row = c.execute(
                "SELECT ready_at FROM npc_cooldowns WHERE user_id=? AND npc_code=? AND action_code=?",
                (int(user_id), str(npc_code), str(action_code)),
            ).fetchone()
        return max(0, int(row["ready_at"]) - int(time.time())) if row else 0

    def npc_set_cooldown(self, user_id, npc_code, action_code, seconds):
        now = int(time.time())
        ready_at = now + max(0, int(seconds))
        with self.connect() as c:
            c.execute(
                """INSERT INTO npc_cooldowns(user_id,npc_code,action_code,ready_at)
                   VALUES(?,?,?,?)
                   ON CONFLICT(user_id,npc_code,action_code)
                   DO UPDATE SET ready_at=excluded.ready_at""",
                (int(user_id), str(npc_code), str(action_code), ready_at),
            )
        return ready_at

    def tune_car(self, user_id, cost=75000, boost=5, max_speed=120):
        with self.connect() as c:
            user = c.execute("SELECT balance FROM users WHERE id=?", (int(user_id),)).fetchone()
            if not user:
                return False, "❌ Игрок не найден."
            car = c.execute(
                "SELECT id,model,speed FROM cars WHERE user_id=? ORDER BY id DESC LIMIT 1",
                (int(user_id),),
            ).fetchone()
            if not car:
                return False, "❌ Сначала купи машину в автосалоне."
            if int(user["balance"]) < int(cost):
                return False, f"❌ Для тюнинга нужно {int(cost):,} $.".replace(",", " ")
            if int(car["speed"]) >= int(max_speed):
                return False, f"⚡ {car['model']} уже достигла максимальной скорости {max_speed}."
            new_speed = min(int(max_speed), int(car["speed"]) + int(boost))
            c.execute("UPDATE users SET balance=balance-? WHERE id=?", (int(cost), int(user_id)))
            c.execute("UPDATE cars SET speed=? WHERE id=?", (new_speed, int(car["id"])))
            return True, (
                f"🔧 ТЮНИНГ ЗАВЕРШЁН\n\n🚗 {car['model']}\n"
                f"⚡ Скорость: {car['speed']} → {new_speed}\n"
                f"💵 Стоимость: {int(cost):,} $".replace(",", " ")
            )

    def get_or_create_user(self, vk_id):
        with self.connect() as c:
            row = c.execute("SELECT * FROM users WHERE vk_id=?", (vk_id,)).fetchone()
            if row:
                return row
            c.execute(
                "INSERT INTO users(vk_id,ref_code,created_at) VALUES(?,?,?)",
                (vk_id, self.new_ref(), int(time.time()))
            )
            row = c.execute("SELECT * FROM users WHERE vk_id=?", (vk_id,)).fetchone()
            nickname = f"Игрок{row['id']}"
            c.execute("UPDATE users SET nickname=? WHERE id=?", (nickname, row["id"]))
            return c.execute("SELECT * FROM users WHERE id=?", (row["id"],)).fetchone()

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

    def status(self,user_id):
        now=int(time.time())
        with self.connect() as c:
            r=c.execute("SELECT * FROM player_status WHERE user_id=?",(user_id,)).fetchone()
            if not r:
                c.execute("INSERT INTO player_status(user_id,heat,reputation,energy,last_update) VALUES(?,?,?,?,?)",(user_id,0,0,100,now))
                return c.execute("SELECT * FROM player_status WHERE user_id=?",(user_id,)).fetchone()
            elapsed=max(0,now-int(r["last_update"]))
            energy=min(100,int(r["energy"])+elapsed//60*5)
            heat=max(0,int(r["heat"])-elapsed//300)
            c.execute("UPDATE player_status SET energy=?,heat=?,last_update=? WHERE user_id=?",(energy,heat,now,user_id))
            return c.execute("SELECT * FROM player_status WHERE user_id=?",(user_id,)).fetchone()

    def status_change(self,user_id,heat=0,reputation=0,energy=0):
        r=self.status(user_id)
        now=int(time.time())
        h=max(0,min(100,int(r["heat"])+int(heat)))
        rep=max(-1000,min(1000,int(r["reputation"])+int(reputation)))
        en=max(0,min(100,int(r["energy"])+int(energy)))
        with self.connect() as c:
            c.execute("UPDATE player_status SET heat=?,reputation=?,energy=?,last_update=? WHERE user_id=?",(h,rep,en,now,user_id))
        return self.status(user_id)

    def city_event_list(self):
        with self.connect() as c:
            return c.execute("SELECT * FROM city_events WHERE active=1 ORDER BY code").fetchall()

    def city_event_seed(self):
        events=[
            ("double_work","⚡ Двойная смена","Сегодня работа приносит повышенную награду.",0,0),
            ("street_rush","🔥 Уличная жара","Рискованные действия дают больше репутации.",0,0),
            ("black_market","🕶️ Чёрный рынок","Особые сделки доступны сегодня.",0,0),
        ]
        with self.connect() as c:
            for row in events:
                c.execute("INSERT OR IGNORE INTO city_events(code,title,description,reward_cash,reward_xp,active) VALUES(?,?,?,?,?,1)",row)

    def user(self, user_id):
        with self.connect() as c:
            return c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

    def user_by_vk(self, vk_id):
        with self.connect() as c:
            return c.execute("SELECT * FROM users WHERE vk_id=?", (int(vk_id),)).fetchone()

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
            "Falcon Compact":("common",52,18_000),"Vektor Sedan":("common",64,35_000),
            "Sultan":("sport",20,8_000_000),"Banshee":("sport",25,12_000_000),
            "Raptor Coupe":("sport",79,65_000),"Night Runner":("sport",91,145_000),
            "Infernus":("super",40,50_000_000),"Turismo":("super",45,65_000_000),
            "Bullet GT":("super",97,250_000),"Phantom X":("super",99,450_000),
            "Savanna":("lowrider",14,5_000_000),"Voodoo":("lowrider",16,6_000_000),
            "Titan SUV":("special",68,90_000),"Iron Wolf":("special",88,180_000)
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


    def mission_add(self, user_id, code, amount=1):
        now = int(time.time())
        with self.connect() as c:
            c.execute(
                "INSERT INTO mission_progress(user_id,code,progress,claimed,updated_at) VALUES(?,?,?,?,?) "
                "ON CONFLICT(user_id,code) DO UPDATE SET progress=progress+excluded.progress,updated_at=excluded.updated_at",
                (user_id, code, max(0, int(amount)), 0, now)
            )

    def mission_rows(self, user_id, codes):
        with self.connect() as c:
            rows = c.execute(
                "SELECT code,progress,claimed FROM mission_progress WHERE user_id=? AND code IN (%s)"
                % ",".join("?" for _ in codes),
                [user_id, *codes]
            ).fetchall()
        return {r["code"]:dict(r) for r in rows}

    def mission_claim(self, user_id, code, reward_cash, reward_xp, target):
        with self.connect() as c:
            row = c.execute(
                "SELECT progress,claimed FROM mission_progress WHERE user_id=? AND code=?",
                (user_id, code)
            ).fetchone()
            if not row or row["claimed"]:
                return False, "❌ Награда уже получена или миссия ещё не выполнена."
            if row["progress"] < target:
                return False, "⏳ Миссия ещё не выполнена."
            c.execute("UPDATE mission_progress SET claimed=1,updated_at=? WHERE user_id=? AND code=?",
                      (int(time.time()), user_id, code))
            c.execute("UPDATE users SET balance=balance+?,xp=xp+? WHERE id=?",
                      (reward_cash, reward_xp, user_id))
            xp = c.execute("SELECT xp FROM users WHERE id=?", (user_id,)).fetchone()["xp"]
            c.execute("UPDATE users SET level=? WHERE id=?", (xp // 100 + 1, user_id))
            return True, f"🎉 МИССИЯ ВЫПОЛНЕНА\n\n💵 +{money(reward_cash)}\n✨ +{reward_xp} XP"

    def casino_record(self, user_id, wager, profit, won):
        now = int(time.time())
        with self.connect() as c:
            c.execute(
                "INSERT INTO casino_stats(user_id,plays,wins,losses,wagered,profit,updated_at) VALUES(?,?,?,?,?,?,?) "
                "ON CONFLICT(user_id) DO UPDATE SET plays=plays+1,wins=wins+excluded.wins,"
                "losses=losses+excluded.losses,wagered=wagered+excluded.wagered,"
                "profit=profit+excluded.profit,updated_at=excluded.updated_at",
                (user_id, 1, 1 if won else 0, 0 if won else 1, wager, profit, now)
            )

    def casino_stats(self, user_id):
        with self.connect() as c:
            return c.execute("SELECT * FROM casino_stats WHERE user_id=?", (user_id,)).fetchone()

    def get_nickname(self, user_id):
        with self.connect() as c:
            row = c.execute(
                "SELECT nickname FROM users WHERE id=?",
                (user_id,)
            ).fetchone()
            if not row:
                return None
            return row["nickname"]

    def set_nickname(self, user_id, nickname):
        nickname = str(nickname).strip()

        if len(nickname) < 3 or len(nickname) > 20:
            return False, "❌ Ник должен содержать от 3 до 20 символов."

        with self.connect() as c:
            row = c.execute(
                "SELECT id FROM users WHERE id=?",
                (user_id,)
            ).fetchone()

            if not row:
                return False, "❌ Игрок не найден."

            exists = c.execute(
                "SELECT id FROM users WHERE nickname=? AND id<>?",
                (nickname, user_id)
            ).fetchone()

            if exists:
                return False, "❌ Такой ник уже занят."

            c.execute(
                "UPDATE users SET nickname=? WHERE id=?",
                (nickname, user_id)
            )

        return True, f"✅ Твой игровой ник изменён на: {nickname}"

    def top(self):
        with self.connect() as c:
            rows=c.execute(
                "SELECT nickname,balance,bank,level,referrals FROM users WHERE banned=0 "
                "ORDER BY balance+bank DESC LIMIT 10"
            ).fetchall()
        if not rows: return "🏆 Пока никого нет."
        return "🏆 ТОП ИГРОКОВ\n\n" + "\n".join(
            f"{i}. 🎭 {r['nickname']} — {money(r['balance']+r['bank'])} | ⭐ {r['level']}"
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

    def get_setting(self, key, default=None):
        with self.connect() as c:
            row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key, value):
        with self.connect() as c:
            c.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(key), str(value))
            )

    def maintenance_mode(self):
        return str(self.get_setting("maintenance_mode", "0")).lower() in {"1", "true", "on", "yes"}

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
            row=c.execute("SELECT id,balance FROM users WHERE vk_id=?",(vk_id,)).fetchone()
            if not row:
                return False
            new_balance=max(0, row["balance"] + int(delta))
            c.execute("UPDATE users SET balance=? WHERE id=?",(new_balance,row["id"]))
            return True

    def admin_level(self,vk_id,level):
        level=max(1,min(100, int(level)))
        with self.connect() as c:
            row=c.execute("SELECT id FROM users WHERE vk_id=?",(vk_id,)).fetchone()
            if not row:
                return False
            c.execute("UPDATE users SET level=? WHERE id=?",(level,row["id"]))
            return True

    def admin_ban(self,vk_id,value):
        with self.connect() as c:
            row=c.execute("SELECT id FROM users WHERE vk_id=?",(vk_id,)).fetchone()
            if not row:
                return False
            c.execute("UPDATE users SET banned=? WHERE id=?",(int(value),row["id"]))
            return True

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
