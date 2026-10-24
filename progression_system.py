"""Daily/weekly contracts and player gangs for Bandit City.

All rewards are granted inside a single SQLite transaction and contract claims
are idempotent per user/task/period.
"""
import time
import sqlite3
from datetime import datetime, timezone

DAILY_TASKS = {
    "work3": {"title": "💼 Выполни 3 рабочие смены", "target": 3, "cash": 12000, "xp": 25, "action": "work"},
    "earn50": {"title": "💵 Получи награды за рабочие смены на 50 000 $", "target": 50000, "cash": 15000, "xp": 30, "action": "earn"},
    "city2": {"title": "🎮 Выполни 2 рабочие смены", "target": 2, "cash": 10000, "xp": 20, "action": "work"},
}
WEEKLY_TASKS = {
    "work15": {"title": "💼 Выполни 15 рабочих смен", "target": 15, "cash": 85000, "xp": 150, "action": "work"},
    "earn300": {"title": "💵 Получи награды за рабочие смены на 300 000 $", "target": 300000, "cash": 100000, "xp": 180, "action": "earn"},
}

def _period(kind, now=None):
    dt = datetime.fromtimestamp(now or time.time(), timezone.utc)
    if kind == "daily":
        return dt.strftime("%Y-%m-%d")
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"

class Progression:
    def __init__(self, db):
        self.db = db
        with db.connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS progression_tasks(
              user_id INTEGER NOT NULL, kind TEXT NOT NULL, period TEXT NOT NULL,
              task_code TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
              claimed INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL,
              PRIMARY KEY(user_id,kind,period,task_code));
            CREATE TABLE IF NOT EXISTS gangs(
              id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
              name TEXT NOT NULL, leader_id INTEGER NOT NULL, treasury INTEGER NOT NULL DEFAULT 0,
              created_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS gang_members(
              gang_id INTEGER NOT NULL, user_id INTEGER NOT NULL, joined_at INTEGER NOT NULL,
              contribution INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY(gang_id,user_id), UNIQUE(user_id));
            CREATE TABLE IF NOT EXISTS gang_ledger(
              id INTEGER PRIMARY KEY AUTOINCREMENT, gang_id INTEGER NOT NULL,
              user_id INTEGER NOT NULL, amount INTEGER NOT NULL, created_at INTEGER NOT NULL);
            """)
    def _ensure(self, c, uid, kind, now=None):
        period = _period(kind, now)
        tasks = DAILY_TASKS if kind == "daily" else WEEKLY_TASKS
        stamp = int(now or time.time())
        for code in tasks:
            c.execute("INSERT OR IGNORE INTO progression_tasks(user_id,kind,period,task_code,updated_at) VALUES(?,?,?,?,?)",
                      (uid, kind, period, code, stamp))
        return period, tasks
    def record(self, uid, action, amount=1, now=None):
        amount = max(0, int(amount))
        stamp = int(now or time.time())
        with self.db.connect() as c:
            for kind, tasks in (("daily", DAILY_TASKS), ("weekly", WEEKLY_TASKS)):
                period, selected = self._ensure(c, int(uid), kind, stamp)
                for code, task in selected.items():
                    if task["action"] == action:
                        c.execute("""UPDATE progression_tasks SET progress=MIN(?,progress+?),updated_at=?
                                     WHERE user_id=? AND kind=? AND period=? AND task_code=? AND claimed=0""",
                                  (task["target"], amount, stamp, int(uid), kind, period, code))
    def view(self, uid, kind="daily", now=None):
        if kind not in ("daily", "weekly"):
            kind = "daily"
        with self.db.connect() as c:
            period, tasks = self._ensure(c, int(uid), kind, now)
            rows = c.execute("SELECT task_code,progress,claimed FROM progression_tasks WHERE user_id=? AND kind=? AND period=? ORDER BY task_code",
                             (int(uid), kind, period)).fetchall()
        lines = [("📅 ЕЖЕДНЕВНЫЕ КОНТРАКТЫ" if kind == "daily" else "🗓️ ЕЖЕНЕДЕЛЬНЫЕ КОНТРАКТЫ"),
                 f"Период: {period}", ""]
        for row in rows:
            task = tasks[row["task_code"]]
            status = "✅ Получено" if row["claimed"] else ("🎁 Можно забрать" if row["progress"] >= task["target"] else f"{row['progress']:,}/{task['target']:,}".replace(",", " "))
            lines.append(f"{task['title']}\n   {status} · награда {task['cash']:,}$ + {task['xp']} XP".replace(",", " "))
        lines += ["", "Прогресс засчитывается за реальные игровые действия."]
        return "\n".join(lines)
    def claim(self, uid, code, kind="daily", now=None):
        if kind not in ("daily", "weekly") or code not in (DAILY_TASKS if kind=="daily" else WEEKLY_TASKS):
            return "❌ Неизвестный контракт."
        stamp = int(now or time.time())
        with self.db.connect() as c:
            period, tasks = self._ensure(c, int(uid), kind, stamp)
            task = tasks[code]
            row = c.execute("SELECT progress,claimed FROM progression_tasks WHERE user_id=? AND kind=? AND period=? AND task_code=?",
                            (int(uid),kind,period,code)).fetchone()
            if row["claimed"]:
                return "ℹ️ Награда за этот контракт уже получена."
            if row["progress"] < task["target"]:
                return f"⏳ Контракт ещё не выполнен: {row['progress']}/{task['target']}."
            c.execute("UPDATE progression_tasks SET claimed=1,updated_at=? WHERE user_id=? AND kind=? AND period=? AND task_code=? AND claimed=0",
                      (stamp,int(uid),kind,period,code))
            if c.execute("SELECT changes()").fetchone()[0] != 1:
                return "ℹ️ Награда уже была обработана."
            c.execute("UPDATE users SET balance=balance+?,xp=xp+? WHERE id=?", (task["cash"],task["xp"],int(uid)))
            return f"🎁 Контракт выполнен!\n+{task['cash']:,}$\n+{task['xp']} XP".replace(",", " ")
    def gang_status(self, uid):
        with self.db.connect() as c:
            row = c.execute("""SELECT g.*,m.contribution FROM gang_members m JOIN gangs g ON g.id=m.gang_id WHERE m.user_id=?""",(int(uid),)).fetchone()
            if not row:
                top=c.execute("SELECT name,code,(SELECT COUNT(*) FROM gang_members m WHERE m.gang_id=g.id) members,treasury FROM gangs g ORDER BY members DESC,treasury DESC LIMIT 5").fetchall()
                return "🏴 БАНДЫ\n\nТы пока не состоишь в банде.\nСоздать: /gang create Название\nВступить: /gang join КОД\n\nТОП БАНД:\n" + ("\n".join(f"{r['name']} · код {r['code']} · {r['members']} уч. · казна {r['treasury']:,}$".replace(",", " ") for r in top) if top else "Пока нет банд.")
            count=c.execute("SELECT COUNT(*) FROM gang_members WHERE gang_id=?",(row["id"],)).fetchone()[0]
            return f"🏴 БАНДА {row['name']}\nКод: {row['code']}\nУчастников: {count}\nКазна: {row['treasury']:,}$\nТвой вклад: {row['contribution']:,}$\n\n/gang donate СУММА\n/gang leave".replace(",", " ")
    def gang_command(self, uid, text):
        parts=text.strip().split(maxsplit=2)
        if len(parts)<2:
            return self.gang_status(uid)
        action=parts[1].lower()
        stamp=int(time.time())
        with self.db.connect() as c:
            member=c.execute("SELECT gang_id FROM gang_members WHERE user_id=?",(int(uid),)).fetchone()
            if action=="create":
                if member: return "❌ Сначала выйди из текущей банды."
                if len(parts)<3 or not 3<=len(parts[2].strip())<=24: return "Использование: /gang create Название (3–24 символа)."
                name=parts[2].strip()
                code=__import__("secrets").token_hex(3).upper()
                try:
                    cur=c.execute("INSERT INTO gangs(code,name,leader_id,created_at) VALUES(?,?,?,?)",(code,name,int(uid),stamp))
                    c.execute("INSERT INTO gang_members(gang_id,user_id,joined_at) VALUES(?,?,?)",(cur.lastrowid,int(uid),stamp))
                except sqlite3.IntegrityError:
                    return "❌ Не удалось создать банду. Попробуй ещё раз."
                return f"🏴 Банда «{name}» создана! Код приглашения: {code}"
            if action=="join":
                if member: return "❌ Ты уже состоишь в банде."
                if len(parts)<3: return "Использование: /gang join КОД"
                gang=c.execute("SELECT id,name FROM gangs WHERE code=?",(parts[2].strip().upper(),)).fetchone()
                if not gang: return "❌ Банда с таким кодом не найдена."
                try: c.execute("INSERT INTO gang_members(gang_id,user_id,joined_at) VALUES(?,?,?)",(gang["id"],int(uid),stamp))
                except sqlite3.IntegrityError: return "❌ Не удалось вступить в банду."
                return f"✅ Ты вступил в банду «{gang['name']}»."
            if action=="leave":
                if not member: return "Ты не состоишь в банде."
                gang=c.execute("SELECT leader_id FROM gangs WHERE id=?",(member["gang_id"],)).fetchone()
                count=c.execute("SELECT COUNT(*) FROM gang_members WHERE gang_id=?",(member["gang_id"],)).fetchone()[0]
                if gang and gang["leader_id"]==int(uid) and count>1: return "Перед выходом лидер должен передать лидерство (эта функция пока недоступна)."
                c.execute("DELETE FROM gang_members WHERE user_id=?",(int(uid),))
                if gang and gang["leader_id"]==int(uid): c.execute("DELETE FROM gangs WHERE id=?",(member["gang_id"],))
                return "Ты вышел из банды."
            if action=="donate":
                if not member: return "❌ Сначала вступи в банду."
                if len(parts)<3 or not parts[2].isdigit(): return "Использование: /gang donate СУММА"
                amount=int(parts[2])
                if amount<=0: return "Сумма должна быть положительной."
                cur=c.execute("UPDATE users SET balance=balance-? WHERE id=? AND balance>=?",(amount,int(uid),amount))
                if cur.rowcount!=1: return "❌ Недостаточно денег."
                c.execute("UPDATE gangs SET treasury=treasury+? WHERE id=?",(amount,member["gang_id"]))
                c.execute("UPDATE gang_members SET contribution=contribution+? WHERE user_id=?",(amount,int(uid)))
                c.execute("INSERT INTO gang_ledger(gang_id,user_id,amount,created_at) VALUES(?,?,?,?)",(member["gang_id"],int(uid),amount,stamp))
                return f"🤝 Вклад в казну банды: {amount:,}$".replace(",", " ")
        return "Команды: /gang · /gang create Название · /gang join КОД · /gang donate СУММА · /gang leave"
