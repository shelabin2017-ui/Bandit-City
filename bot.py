import logging
import os
import random
import threading
import time
from pathlib import Path

import requests
import vk_api
from dotenv import load_dotenv
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType

from db import Database
from game import Game
from v5 import bridge as v5
from admin_panel import AdminPanel
from roles import RoleManager
from role_ui import RoleUI

load_dotenv()
TOKEN = os.getenv("VK_TOKEN", "").strip()
GROUP_ID = int(os.getenv("GROUP_ID", "0") or 0)
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
if not TOKEN or not GROUP_ID:
    raise SystemExit("Заполни VK_TOKEN и GROUP_ID в .env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
db = Database(os.getenv("DB_PATH", "bandit.db"))
roles = RoleManager(db)
roles.bootstrap_from_env()
for _legacy_uid in ADMIN_IDS:
    roles.ensure_player(_legacy_uid)
role_ui = RoleUI(roles)
game = Game(db, ADMIN_IDS)
admin = AdminPanel(db, game, ADMIN_IDS, roles=roles, role_ui=role_ui)
session = vk_api.VkApi(token=TOKEN)
vk = session.get_api()
longpoll = VkLongPoll(session)

CARD_CACHE = {}
CARD_DIR = Path(__file__).resolve().parent / "assets" / "cards"
INPUT_STATE = {}
MAINTENANCE_KEY = "maintenance_mode"
BROADCAST_COOLDOWN = 60
BROADCAST_LAST = {}
BROADCAST_INTERVAL = 0.12


def money(n):
    return f"${int(n):,}".replace(",", " ")


def set_state(uid, mode, **data):
    INPUT_STATE[uid] = {"mode": mode, **data}


def clear_state(uid):
    INPUT_STATE.pop(uid, None)


def maintenance_enabled():
    try:
        return str(db.get_setting(MAINTENANCE_KEY) or "0") == "1"
    except Exception:
        return False


def build_keyboard(rows):
    k = VkKeyboard(one_time=False)
    clean = []
    for row in rows or []:
        if isinstance(row, str):
            row = [row]
        row = [str(x)[:40] for x in row if x]
        for i in range(0, len(row), 2):
            clean.append(row[i:i + 2])
    # VK rejects default keyboards with more than 10 rows.
    # Keep the bot alive even if a future handler accidentally returns too many.
    if len(clean) > 10:
        logging.warning("Keyboard truncated from %s to 10 rows", len(clean))
        clean = clean[:10]
    for ri, row in enumerate(clean):
        for i, label in enumerate(row):
            low = label.lower()
            if "назад" in low or "главное меню" in low:
                color = VkKeyboardColor.SECONDARY
            elif any(x in low for x in ("купить", "бонус", "подтверд", "положить", "снять", "перевод")):
                color = VkKeyboardColor.POSITIVE
            elif any(x in low for x in ("казино", "удалить", "заблок", "сброс")):
                color = VkKeyboardColor.NEGATIVE
            else:
                color = VkKeyboardColor.PRIMARY
            k.add_button(label, color)
        if ri < len(clean) - 1:
            k.add_line()
    return k


def send(user_id, text, rows=None, attachment=None):
    payload = {"user_id": user_id, "random_id": random.randint(1, 2_147_483_647), "message": str(text)}
    if rows:
        payload["keyboard"] = rows.get_keyboard() if isinstance(rows, VkKeyboard) else build_keyboard(rows).get_keyboard()
    if attachment:
        payload["attachment"] = attachment
    try:
        vk.messages.send(**payload)
    except Exception as exc:
        msg = str(exc)
        if "911" in msg or "100" in msg:
            payload.pop("keyboard", None)
            vk.messages.send(**payload)
        else:
            raise


def execute_broadcast(admin_uid, message):
    """Send one confirmed admin broadcast to every eligible player except sender."""
    admin_uid = int(admin_uid)
    message = str(message or "").strip()
    home = [[role_ui.main_button(admin_uid) or "👑 Админ-панель"]]
    if not message:
        send(admin_uid, "❌ Нельзя отправить пустую рассылку.", home)
        return

    last = BROADCAST_LAST.get(admin_uid, 0)
    remaining = BROADCAST_COOLDOWN - (time.time() - last)
    if remaining > 0:
        send(admin_uid, f"⏳ Повтори рассылку через {int(remaining) + 1} сек.", home)
        return

    with db.connect() as c:
        targets = [
            int(row["vk_id"])
            for row in c.execute(
                "SELECT vk_id FROM users WHERE banned=0 AND vk_id!=? ORDER BY id",
                (admin_uid,),
            ).fetchall()
        ]

    BROADCAST_LAST[admin_uid] = time.time()
    payload_message = "📢 BANDIT CITY\n\n" + message
    sent = 0
    failed = 0

    for target in targets:
        try:
            vk.messages.send(
                user_id=target,
                random_id=random.randint(1, 2_147_483_647),
                message=payload_message,
            )
            sent += 1
        except Exception:
            failed += 1
            logging.exception("Broadcast failed for target %s", target)
        time.sleep(BROADCAST_INTERVAL)

    try:
        admin._log(admin_uid, "broadcast", None, f"sent={sent};failed={failed};targets={len(targets)}")
    except Exception:
        logging.exception("Failed to write broadcast admin log")

    send(
        admin_uid,
        f"📢 Рассылка завершена.\n\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}\n👥 Получателей: {len(targets)}",
        home,
    )


def card_key(text):
    t = str(text).lower()
    if "админ" in t or "admin" in t or "статист" in t:
        return "admin"
    if "магазин" in t or "оруж" in t or "одежд" in t:
        return "shop"
    if "профил" in t or "создател" in t:
        return "profile"
    if "авто" in t or "гараж" in t:
        return "garage"
    if "промокод" in t:
        return "promo"
    return "main"


def upload_card(user_id, key):
    if key in CARD_CACHE:
        return CARD_CACHE[key]
    try:
        import cairosvg
        svg = CARD_DIR / f"{key}.svg"
        png = CARD_DIR / f"{key}.png"
        if not svg.exists():
            return None
        if not png.exists() or png.stat().st_mtime < svg.stat().st_mtime:
            cairosvg.svg2png(url=str(svg), write_to=str(png), output_width=1200, output_height=630)
        upload = vk.photos.getMessagesUploadServer(peer_id=user_id)
        with png.open("rb") as fh:
            response = requests.post(upload["upload_url"], files={"photo": fh}, timeout=30).json()
        saved = vk.photos.saveMessagesPhoto(server=response["server"], photo=response["photo"], hash=response["hash"])
        photo = saved[0]
        attachment = f"photo{photo['owner_id']}_{photo['id']}"
        CARD_CACHE[key] = attachment
        return attachment
    except Exception:
        return None


def send_card(user_id, text, rows=None):
    # Админская панель должна отправляться без карточки:
    # VK иногда отклоняет комбинацию attachment + keyboard,
    # после чего fallback удаляет клавиатуру.
    t = str(text).lower()
    if "админ" in t or "настройки" in t or "технический режим" in t:
        send(user_id, text, rows)
        return
    send(user_id, text, rows, upload_card(user_id, card_key(text)))


def kb_main(is_admin=False, panel_label="👑 Админ-панель"):
    # VK default keyboard supports at most 10 rows. Keep the main screen
    # within that limit and move secondary sections into a separate page.
    rows = [
        ["👤 Профиль", "💼 Работа"],
        ["🚗 Авто", "🛒 Магазин"],
        ["🏢 Бизнес", "🏦 Банк"],
        ["🎰 Казино", "🎁 Бонус"],
        ["👥 Игроки", "🏆 Рейтинг"],
        ["🏆 Достижения", "🎯 Миссии"],
        ["📊 Мой статус", "🌆 События города"],
        ["📱 Телефон", "📩 СМС"],
        ["⚙️ Настройки", "❓ Помощь"],
        ["📚 Ещё", panel_label] if is_admin else ["📚 Ещё"],
    ]
    return rows
