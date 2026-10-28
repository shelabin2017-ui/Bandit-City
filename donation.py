"""Manual donation/order requests for Bandit City. No payment automation."""
import time

# Стартовые скидки для молодого проекта. В подписи указана реальная скидка
# относительно обычной цены; при необходимости проценты и цены можно обновить.
SERVICES = {
    "💵 500 000 игровой валюты — 99 ₽ (скидка 23%)": ("cash_500k", "500 000 игровой валюты", 99),
    "💵 1 000 000 игровой валюты — 179 ₽ (скидка 22%)": ("cash_1m", "1 000 000 игровой валюты", 179),
    "💵 2 000 000 игровой валюты — 249 ₽ (скидка 24%)": ("cash_2m", "2 000 000 игровой валюты", 249),
    "💵 5 000 000 игровой валюты — 449 ₽ (скидка 25%)": ("cash_5m", "5 000 000 игровой валюты", 449),
    "💵 10 000 000 игровой валюты — 699 ₽ (скидка 22%)": ("cash_10m", "10 000 000 игровой валюты", 699),
    "💵 25 000 000 игровой валюты — 1 299 ₽ (скидка 24%)": ("cash_25m", "25 000 000 игровой валюты", 1299),
    "⭐ +1 уровень — 149 ₽ (скидка 25%)": ("level_plus", "+1 уровень", 149),
    "⭐ +3 уровня — 399 ₽ (скидка 27%)": ("level_plus_3", "+3 уровня", 399),
    "⭐ +5 уровней — 599 ₽ (скидка 25%)": ("level_plus_5", "+5 уровней", 599),
    "🚗 Автомобиль — от 199 ₽ (скидка 33%)": ("car", "Выбранный автомобиль", 199),
    "🚘 Премиум-автомобиль — от 399 ₽ (скидка 27%)": ("premium_car", "Премиум-автомобиль на выбор", 399),
    "📝 Индивидуальный заказ": ("custom", "Индивидуальный заказ (цена по договорённости)", 0),
}
PAYMENT_DETAILS = "🏦 Альфа-Банк\nПолучатель: Шелабин Андрей В.\nТелефон: +79083017733"

def ensure_schema(db):
    with db.connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS donation_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            vk_id INTEGER NOT NULL,
            nickname TEXT NOT NULL DEFAULT '',
            service_code TEXT NOT NULL,
            service_title TEXT NOT NULL,
            price_rub INTEGER NOT NULL DEFAULT 0,
            details TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'new',
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            admin_vk INTEGER
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_donation_requests_status ON donation_requests(status,id)")

def create_request(db, user, service_label, details=''):
    ensure_schema(db)
    service = SERVICES.get(service_label)
    if not service:
        return None, "Неизвестная услуга."
    code, title, price = service
    now = int(time.time())
    with db.connect() as c:
        cur = c.execute("""INSERT INTO donation_requests
            (user_id,vk_id,nickname,service_code,service_title,price_rub,details,status,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,'new',?,?)""",
            (int(user["id"]), int(user["vk_id"]), str(user["nickname"] or ""), code, title, price, str(details or ""), now, now))
        rid = cur.lastrowid
    if code == "custom":
        return rid, (
            f"📝 ЗАЯВКА НА ИНДИВИДУАЛЬНЫЙ ЗАКАЗ №{rid}\n\n"
            f"Описание: {details}\n\n"
            "Администратор проверит возможность выполнения и сообщит окончательную цену. "
            "Пока не переводи деньги: эта заявка не является счётом на оплату."
        )
    return rid, (
        f"💎 ЗАЯВКА №{rid}\n\nУслуга: {title}\n"
        + (f"Сумма: {price} ₽\n\n" if price else "Стоимость: по договорённости\n\n")
        + PAYMENT_DETAILS + "\n\nПосле перевода нажми «💳 Я оплатил» в меню доната. "
          "Оплата будет проверена вручную администратором. Создание заявки не означает, что платёж получен."
    )

def set_price(db, request_id, price, admin_vk):
    price = int(price)
    if price < 1 or price > 100000:
        return False
    ensure_schema(db)
    with db.connect() as c:
        cur = c.execute(
            "UPDATE donation_requests SET price_rub=?,status='quoted',updated_at=?,admin_vk=? WHERE id=? AND service_code='custom' AND status='new'",
            (price, int(time.time()), int(admin_vk), int(request_id)),
        )
        return cur.rowcount > 0

def get_request(db, request_id):
    ensure_schema(db)
    with db.connect() as c:
        return c.execute("SELECT * FROM donation_requests WHERE id=?", (int(request_id),)).fetchone()

def set_status(db, request_id, status, admin_vk):
    allowed = {
        "new": {"awaiting", "cancelled"},
        "quoted": {"new", "cancelled"},
        "awaiting": {"paid", "cancelled"},
        "paid": {"granted", "cancelled"},
        "granted": {"completed"},
        "completed": set(),
        "cancelled": set(),
    }
    ensure_schema(db)
    with db.connect() as c:
        row = c.execute("SELECT status FROM donation_requests WHERE id=?", (int(request_id),)).fetchone()
        if not row or status not in allowed.get(row["status"], set()):
            return False
        cur = c.execute(
            "UPDATE donation_requests SET status=?,updated_at=?,admin_vk=? WHERE id=? AND status=?",
            (status, int(time.time()), int(admin_vk), int(request_id), row["status"]),
        )
        return cur.rowcount > 0

def list_requests(db, limit=10):
    """Return active requests; completed/cancelled requests remain in history."""
    ensure_schema(db)
    with db.connect() as c:
        return c.execute(
            "SELECT * FROM donation_requests WHERE status NOT IN ('completed','cancelled') ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()

STATUS = {"new":"🆕 Новая","quoted":"💬 Цена предложена, ждём согласия","awaiting":"🕒 Ожидает оплаты","paid":"💳 Оплата подтверждена","granted":"🎁 Выдача выполнена","completed":"✅ Завершена","cancelled":"❌ Отменена"}
TEMPLATES = {
    "📨 Заявка принята": "📨 Заявка №{id} принята. Услуга: {service}. Это сообщение не подтверждает оплату.",
    "🕒 Ожидаем оплату": "🕒 По заявке №{id} ожидаем оплату. После перевода сообщи об этом в меню доната. Не отправляй данные карты или коды подтверждения.",
    "💳 Оплата подтверждена": "💳 Оплата по заявке №{id} проверена и подтверждена. Готовим выдачу услуги.",
    "🎁 Покупка выдана": "🎁 По заявке №{id} услуга «{service}» выдана. Спасибо за поддержку Bandit City!",
    "❌ Заявка отменена": "❌ Заявка №{id} отменена. Если это ошибка, обратись к администрации Bandit City.",
}
