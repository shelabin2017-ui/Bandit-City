"""Additive business portfolio for Bandit City.

This module keeps new businesses in a separate table so the legacy one-business
airport table and its existing unique constraint remain untouched.
"""
import time

from game import money

BUSINESSES = {
    "kiosk": {"title": "🏪 Продуктовый киоск", "price": 250_000, "income": 450},
    "car_wash": {"title": "🚿 Автомойка", "price": 750_000, "income": 1_200},
    "cafe": {"title": "☕ Городское кафе", "price": 2_000_000, "income": 3_200},
    "workshop": {"title": "🔧 Автомастерская", "price": 5_000_000, "income": 7_500},
    "logistics": {"title": "🚚 Логистическая компания", "price": 15_000_000, "income": 19_000},
    "hotel": {"title": "🏨 Отель Los Santos", "price": 50_000_000, "income": 55_000},
}


def ensure_schema(db):
    with db.connect() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS business_portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                business_type TEXT NOT NULL,
                balance INTEGER NOT NULL DEFAULT 0,
                last_tick INTEGER NOT NULL,
                UNIQUE(user_id, business_type)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_business_portfolio_user ON business_portfolio(user_id)")


def _tick(db, user_id, now=None):
    ensure_schema(db)
    now = int(time.time()) if now is None else int(now)
    with db.connect() as c:
        rows = c.execute("SELECT * FROM business_portfolio WHERE user_id=?", (user_id,)).fetchall()
        total = 0
        for row in rows:
            minutes = min(24 * 60, max(0, (now - int(row["last_tick"])) // 60))
            if minutes <= 0:
                continue
            rate = BUSINESSES.get(row["business_type"], {}).get("income", 0)
            earned = minutes * rate
            next_tick = now if now - int(row["last_tick"]) >= 24 * 60 * 60 else int(row["last_tick"]) + minutes * 60
            c.execute(
                "UPDATE business_portfolio SET balance=balance+?, last_tick=? WHERE id=?",
                (earned, next_tick, row["id"]),
            )
            total += earned
        return total


def buy_business(db, user_id, code):
    ensure_schema(db)
    item = BUSINESSES.get(code)
    if not item:
        return "❌ Такого бизнеса нет."
    with db.connect() as c:
        existing = c.execute(
            "SELECT 1 FROM business_portfolio WHERE user_id=? AND business_type=?",
            (user_id, code),
        ).fetchone()
        if existing:
            return "❌ Этот бизнес у тебя уже есть."
        user = c.execute("SELECT balance FROM users WHERE id=?", (user_id,)).fetchone()
        if not user:
            return "❌ Игрок не найден."
        if int(user["balance"]) < item["price"]:
            return f"❌ Не хватает денег. Цена: {money(item['price'])}."
        now = int(time.time())
        c.execute("UPDATE users SET balance=balance-? WHERE id=?", (item["price"], user_id))
        c.execute(
            "INSERT INTO business_portfolio(user_id,business_type,balance,last_tick) VALUES(?,?,0,?)",
            (user_id, code, now),
        )
        c.execute(
            "INSERT INTO transactions(from_user,to_user,amount,type,created_at) VALUES(NULL,?,?,?,?)",
            (user_id, item["price"], "business_portfolio_buy", now),
        )
    return f"✅ Куплено: {item['title']}\n💵 Цена: {money(item['price'])}\n📈 Доход: {money(item['income'])}/мин."


def portfolio_text(db, user_id):
    _tick(db, user_id)
    with db.connect() as c:
        rows = c.execute(
            "SELECT business_type,balance FROM business_portfolio WHERE user_id=? ORDER BY id",
            (user_id,),
        ).fetchall()
    if not rows:
        return (
            "🏢 ПОРТФЕЛЬ БИЗНЕСОВ\n\nПока дополнительных бизнесов нет.\n"
            "Покупай киоск, автомойку, кафе, СТО, логистику или отель.\n"
            "Доход начисляется автоматически, максимум за 24 часа между проверками."
        )
    lines = ["🏢 ТВОИ БИЗНЕСЫ", ""]
    total = 0
    for row in rows:
        item = BUSINESSES.get(row["business_type"], {})
        balance = int(row["balance"])
        total += balance
        lines.append(f"{item.get('title', row['business_type'])}\n💵 Касса: {money(balance)} • 📈 {money(item.get('income', 0))}/мин")
    lines.extend(["", f"💰 Всего к снятию: {money(total)}", "📈 Доход начисляется автоматически (лимит офлайн-начисления — 24 часа)."])
    return "\n".join(lines)


def withdraw_income(db, user_id):
    _tick(db, user_id)
    with db.connect() as c:
        rows = c.execute(
            "SELECT COALESCE(SUM(balance),0) AS amount FROM business_portfolio WHERE user_id=?",
            (user_id,),
        ).fetchone()
        amount = int(rows["amount"])
        if amount <= 0:
            return "💸 Пока нечего снимать: кассы новых бизнесов пусты."
        c.execute("UPDATE business_portfolio SET balance=0 WHERE user_id=?", (user_id,))
        c.execute("UPDATE users SET balance=balance+? WHERE id=?", (amount, user_id))
        c.execute(
            "INSERT INTO transactions(from_user,to_user,amount,type,created_at) VALUES(NULL,?,?,?,?)",
            (user_id, amount, "business_portfolio_withdraw", int(time.time())),
        )
    return f"💰 Доход снят: {money(amount)}."


def tick_all_portfolios(db):
    """Accrue passive income for every portfolio from the existing business worker."""
    ensure_schema(db)
    with db.connect() as c:
        user_ids = [int(row["user_id"]) for row in c.execute(
            "SELECT DISTINCT user_id FROM business_portfolio"
        ).fetchall()]
    for user_id in user_ids:
        _tick(db, user_id)
