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
from release import announce_new_release

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
    if "ивент" in t or "midnight" in t or "midnight run" in t or "событ" in t:
        return "event"
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


def kb_more():
    return [
        ["📖 Сюжет", "🎓 Обучение"],
        ["🏆 Ачивки", "🎟 Промокод"],
        ["👑 О создателе"],
        ["🏙️ Главное меню"],
    ]


def has_admin_access(uid):
    return int(uid) in ADMIN_IDS or roles.has(uid, "economy.manage")


def main_kb(uid):
    label = role_ui.main_button(uid)
    if label:
        return kb_main(True, label)
    if has_admin_access(uid):
        return kb_main(True)
    return kb_main(False)


def has_staff_access(uid):
    return bool(role_ui.main_button(uid)) or has_admin_access(uid)


def kb_bank():
    return [["💵 Положить $10k", "💸 Снять $10k"], ["💵 Внести сумму", "💸 Снять сумму"], ["🏙️ Главное меню"]]


def kb_business():
    return [["🏭 Купить аэропорт", "📦 Склад"], ["📦 Пополнить склад", "💰 Снять деньги"], ["ℹ️ Инфо", "🏙️ Главное меню"]]


def kb_work():
    return [["🚕 Таксист", "🕵️ Федерал"], ["📦 Блок", "🔗 Рефка"], ["🏙️ Главное меню"]]


def kb_auto():
    return [["🚙 Обычные", "🏎 Спорт"], ["🔥 Суперкары", "💿 Лоурайдеры"], ["🚘 Спецтранспорт", "🚘 Гараж"], ["🏙️ Главное меню"]]


def kb_casino():
    return [["🎲 Кости", "🎰 Слоты"], ["🎯 Рулетка", "🃏 Blackjack"], ["📊 Статистика казино"], ["🏙️ Главное меню"]]

def kb_phone():
    return [["👥 Контакты", "➕ Добавить контакт"], ["➖ Удалить контакт"], ["🤝 NPC города"], ["🏙️ Главное меню"]]

NPC_ACTION_BUTTONS = {
    "dealer": "💰 Сделка дилера",
    "fixer": "📜 Заказ фиксера",
    "mechanic": "🔧 Тюнинг авто",
    "informant": "🕵️ Слух информатора",
}


def kb_npc(code=None):
    if code in NPC_ACTION_BUTTONS:
        return [[NPC_ACTION_BUTTONS[code]], ["📱 Телефон"], ["🏙️ Главное меню"]]
    return [["💰 Дилер", "🕴️ Фиксер"], ["🔧 Механик", "🕵️ Информатор"], ["📱 Телефон"], ["🏙️ Главное меню"]]


def kb_settings():
    return [
        ["🎭 Изменить ник"],
        ["🏙️ Главное меню"],
    ]


def help_text():
    return (
        "❓ BANDIT CITY — ПОМОЩЬ\n\n"
        "🏙️ Ты находишься в криминальном городе, где деньги — только начало.\n\n"
        "💼 Работа — заработок и XP\n🏢 Бизнес — пассивный доход\n🚗 Авто — каталог и гараж\n🛒 Магазин — вещи, одежда, оружие и премиум\n🏦 Банк — хранилище денег\n🎰 Казино — риск и награда\n👥 Игроки — переводы, атаки и рефералы\n🎟 Промокод — секретные дропы\n🏆 Рейтинг / достижения — твой прогресс\n\n"
        "⌨️ Команды: /bank in SUM, /bank out SUM, /pay VK_ID SUM, /stock SUM, /top, /daily, /achievements, /ref."
    )


def creator_text():
    return (
        "👑 СОЗДАТЕЛЬ BANDIT CITY\n\n"
        "🏙️ BANDIT CITY — город, который создан с нуля.\n\n"
        "👤 Автор и создатель проекта — Андрей Шелабин.\n\n"
        "🎮 Идея проекта — собрать в одном VK-боте живой криминальный город: "
        "работу, бизнес, машины, магазин, казино, рейтинг, игроков, прокачку "
        "и собственную атмосферу.\n\n"
        "🛠️ Проект развивается постепенно. "
        "Новые механики, события, предметы и возможности появляются по мере "
        "развития города.\n\n"
        "🖤 BANDIT CITY — это не просто бот. "
        "Это город, который строится вместе с игроками.\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔗 МОИ ССЫЛКИ\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🌐 VK — [https://vk.ru/zeromer_offical|zeromer_offical]\n"
        "▶️ YouTube — @zeromertv\n"
        "🎵 TikTok — @zeroshkayt\n"
        "💬 Telegram — @zeroshka_greshnika\n"
        "📢 Telegram-канал — https://t.me/zeroshkaoff"
    )


def process_input(uid, text):
    st = INPUT_STATE.get(uid)
    if not st:
        return False
    low = text.lower().strip()
    if low in ("отмена", "❌ отмена", "/cancel"):
        clear_state(uid)
        send_card(uid, "❌ Операция отменена.", main_kb(uid))
        return True
    try:
        if st["mode"] == "bank_in":
            amount = int(text.replace(" ", ""))
            clear_state(uid)
            send(uid, game.bank(db.get_or_create_user(uid)["id"], "deposit", amount), kb_bank())
            return True
        if st["mode"] == "bank_out":
            amount = int(text.replace(" ", ""))
            clear_state(uid)
            send(uid, game.bank(db.get_or_create_user(uid)["id"], "withdraw", amount), kb_bank())
            return True
        if st["mode"] == "pay":
            p = text.split()
            target, amount = int(p[0]), int(p[1])
            clear_state(uid)
            send(uid, game.transfer(db.get_or_create_user(uid)["id"], target, amount), main_kb(uid))
            return True
        if st["mode"] == "nickname":
            import re

            nickname = " ".join(text.strip().split())

            if len(nickname) < 3 or len(nickname) > 20:
                send(uid, "❌ Ник должен содержать от 3 до 20 символов.\n\nПопробуй ещё раз.", [["❌ Отмена"]])
                return True

            if not re.fullmatch(r"[A-Za-zА-Яа-яЁё0-9_ -]+", nickname):
                send(uid, "❌ В нике разрешены только буквы, цифры, пробел, _ и -.\n\nПопробуй ещё раз.", [["❌ Отмена"]])
                return True

            ok, message = db.set_nickname(db.get_or_create_user(uid)["id"], nickname)
            if ok:
                clear_state(uid)
                send_card(uid, message, kb_settings())
            else:
                send(uid, message, [["❌ Отмена"]])
            return True

        if st["mode"] == "phone_add":
            msg=game.phone_add(db.get_or_create_user(uid)["id"], int(text.replace(" ","")))
            clear_state(uid); send(uid,msg,kb_phone()); return True
        if st["mode"] == "phone_remove":
            msg=game.phone_remove(db.get_or_create_user(uid)["id"], int(text.replace(" ","")))
            clear_state(uid); send(uid,msg,kb_phone()); return True
        if st["mode"] == "stock":
            amount = int(text.replace(" ", ""))
            clear_state(uid)
            send(uid, game.refill_stock(db.get_or_create_user(uid)["id"], amount), kb_business())
            return True
    except (ValueError, IndexError):
        send(uid, "❌ Неверный формат. Введи число и попробуй снова.\nИли нажми «❌ Отмена».", [["❌ Отмена"]])
        return True
    return False


def execute_broadcast(uid, message):
    last = BROADCAST_LAST.get(uid, 0)
    remaining = BROADCAST_COOLDOWN - (time.time() - last)
    if remaining > 0:
        send(uid, "⏳ Повтори рассылку через {} сек.".format(int(remaining) + 1), [[role_ui.main_button(uid) or "👑 Админ-панель"]])
        return

    BROADCAST_LAST[uid] = time.time()
    with db.connect() as c:
        targets = [int(r["vk_id"]) for r in c.execute(
            "SELECT vk_id FROM users WHERE banned=0 ORDER BY id"
        ).fetchall()]

    logging.info("Broadcast start: admin=%s total=%s", uid, len(targets))
    sent = 0
    skipped = 0
    failed = 0

    for target in targets:
        try:
            allowed = True
            try:
                check = vk.messages.isMessagesFromGroupAllowed(
                    group_id=GROUP_ID,
                    user_id=target,
                )
                allowed = bool(check.get("is_allowed", 0))
            except Exception:
                # Older/limited VK API wrappers may not expose the check.
                # In that case try the actual send and log the VK response/error.
                logging.warning("Broadcast permission check unavailable for %s", target)

            if not allowed:
                skipped += 1
                logging.warning("Broadcast skipped for %s: messages from group are not allowed", target)
                continue

            result = vk.messages.send(
                user_id=target,
                random_id=random.randint(1, 2_147_483_647),
                message="📢 BANDIT CITY\n\n" + str(message),
            )
            sent += 1
            logging.info("Broadcast sent: target=%s message_id=%s", target, result)
            time.sleep(0.35)
        except Exception as exc:
            failed += 1
            logging.exception("Broadcast failed for %s: %s", target, exc)

    logging.info(
        "Broadcast finished: admin=%s sent=%s skipped=%s failed=%s total=%s",
        uid, sent, skipped, failed, len(targets)
    )
    send(
        uid,
        "📢 Результат рассылки\n\n"
        "✅ Отправлено: {}\n"
        "⏭️ Пропущено: {}\n"
        "❌ Ошибок: {}\n"
        "👥 Всего игроков: {}".format(sent, skipped, failed, len(targets)),
        [[role_ui.main_button(uid) or "👑 Админ-панель"]],
    )
def process(uid, text):
    text = text.strip()
    low = text.lower()
    if process_input(uid, text):
        return

    user = db.get_or_create_user(uid)
    if maintenance_enabled() and not has_staff_access(uid):
        send_card(uid, "🏙️ BANDIT CITY\n\n🚧 ТЕХНИЧЕСКИЕ РАБОТЫ\n\nГород временно закрыт на обслуживание.\n\n🛠️ Мы обновляем систему, исправляем ошибки\nи готовим новые возможности.\n\n⏳ Совсем скоро город снова откроется.\n\n🖤 Спасибо за ожидание.")
        return
    if db.is_banned(uid):
        send(uid, "⛔ Твой аккаунт заблокирован.")
        return

    if db.needs_onboarding(user["id"]):
        # Handle tutorial navigation before the generic welcome branch.
        # Otherwise every "▶️ Далее" hits needs_onboarding() again and
        # returns to step 1 forever.
        if text == "▶️ Далее":
            message = game.tutorial_next(user["id"])
            if "ЗАВЕРШЕНО" in message:
                send_card(uid, message, main_kb(uid))
            else:
                send(uid, message, [["▶️ Далее"]])
            return

        if text == "🎓 Обучение":
            send(uid, game.tutorial(user["id"]), [["▶️ Далее"]])
            return

        referral_bonus = False
        if low.startswith("/start"):
            parts = text.split(maxsplit=1)
            if len(parts) == 2:
                referral_bonus = bool(game.apply_referral(user["id"], parts[1]))
        send_card(uid, game.welcome(user["id"], referral_bonus), [["🎓 Обучение"]])
        send(uid, game.tutorial(user["id"]), [["▶️ Далее"]])
        return

    if low.startswith("/start") or low in ("/menu", "меню", "🏙️ главное меню"):
        send_card(uid, "🏙 Главное меню", main_kb(uid))
        return
    if low in ("/info", "инфо", "👤 профиль"):
        send_card(uid, game.profile(user["id"]), main_kb(uid))
        return
    if text == "📚 Ещё":
        send_card(uid, "📚 ДОПОЛНИТЕЛЬНО\n\nВыбери нужный раздел:", kb_more())
        return

    if text == "⚙️ Настройки":
        if has_admin_access(uid):
            handled, admin_text, admin_rows = admin.handle(uid, text)
            if handled:
                send(uid, admin_text, admin_rows)
                return

        send_card(uid, "⚙️ НАСТРОЙКИ\n\nЗдесь можно изменить данные твоего игрового профиля.", kb_settings())
        return

    if text == "🎭 Изменить ник":
        set_state(uid, "nickname")
        send(uid, "🎭 ИЗМЕНЕНИЕ НИКА\n\nВведи новый игровой ник.\n\n📏 От 3 до 20 символов.\n🔤 Можно использовать буквы, цифры, пробел, _ и -.", [["❌ Отмена"]])
        return

    if text == "❓ Помощь":
        send_card(uid, help_text(), main_kb(uid))
        return
    if text == "👑 О создателе":
        send_card(uid, creator_text(), [["🏙️ Главное меню"]])
        return

    if text == "📊 Мой статус":
        send(uid, game.status(user["id"]), [["👤 Профиль"],["🌆 События города"],["🏙️ Главное меню"]]); return
    if text == "🌆 События города":
        send(uid, game.city_events(user["id"]), [["📊 Мой статус"],["🏙️ Главное меню"]]); return
    if text == "💼 Работа":
        send(uid, "💼 ВЫБЕРИ РАБОТУ", kb_work())
        return
    work_map = {"🚕 Таксист": "taxi", "🕵️ Федерал": "federal", "📦 Блок": "block", "🔗 Рефка": "refwork"}
    if text in work_map:
        send(uid, game.work(user["id"], work_map[text]), kb_work())
        return

    if text == "🏢 Бизнес":
        send(uid, game.business_info(user["id"]), kb_business())
        return
    if text == "🏭 Купить аэропорт":
        send(uid, game.buy_business(user["id"]), kb_business())
        return
    if text in ("📦 Склад", "ℹ️ Инфо"):
        send(uid, game.business_info(user["id"]), kb_business())
        return
    if text == "💰 Снять деньги":
        send(uid, game.withdraw_business(user["id"]), kb_business())
        return
    if text == "📦 Пополнить склад":
        set_state(uid, "stock")
        send(uid, "📦 Введи количество сырья для пополнения склада:\n\nПример: 250", [["❌ Отмена"]])
        return
    if low.startswith("/stock "):
        try:
            send(uid, game.refill_stock(user["id"], int(text.split()[1])), kb_business())
        except (ValueError, IndexError):
            send(uid, "Использование: /stock КОЛИЧЕСТВО", kb_business())
        return

    if text == "🚗 Авто":
        send(uid, "🚗 АВТОСАЛОН LOS SANTOS", kb_auto())
        return
    cats = {"🚙 Обычные": "common", "🏎 Спорт": "sport", "🔥 Суперкары": "super", "💿 Лоурайдеры": "lowrider", "🚘 Спецтранспорт": "special"}
    if text in cats:
        send(uid, game.catalog(cats[text]), kb_auto())
        return
    if text == "🚘 Гараж" or low == "/garage":
        send(uid, game.garage(user["id"]), kb_auto())
        return
    if low.startswith("/buycar "):
        try:
            model = text.split(maxsplit=1)[1].strip()
            if not model:
                raise ValueError
            send(uid, game.buy_car(user["id"], model), kb_auto())
        except (ValueError, IndexError):
            send(uid, "Использование: /buycar МОДЕЛЬ", kb_auto())
        return
    if low.startswith("/sellcar "):
        try:
            send(uid, game.sell_car(user["id"], int(text.split()[1])), kb_auto())
        except (ValueError, IndexError):
            send(uid, "Использование: /sellcar ID", kb_auto())
        return

    if text == "🛒 Магазин":
        msg, buttons = v5.shop_hub(); send(uid, msg, buttons); return
    if text == "🛍️ Предметы":
        msg, buttons = v5.item_shop(); send(uid, msg, buttons); return
    if text == "🎒 Инвентарь":
        msg, buttons = v5.inventory(db, uid); send(uid, msg, buttons); return
    if text in ("🧥 Одежда", "👕 Одежда"):
        msg, buttons = v5.clothing_menu(); send(uid, msg, buttons); return
    character_category_map = {
        "🧢 Головной убор": "🧢 Головные уборы",
        "💇 Волосы": "💇 Волосы",
        "💍 Аксессуары": "💍 Аксессуары",
        "👖 Брюки": "👖 Брюки",
        "🥾 Обувь": "🥾 Обувь",
    }
    if text in character_category_map:
        msg, buttons = v5.clothing_catalog(db, uid, character_category_map[text]); send(uid, msg, buttons); return
    if text == "🎪 Ивент-дропы":
        msg, buttons = v5.event_catalog(); send(uid, msg, buttons); return
    if text in v5.CLOTHING:
        msg, buttons = v5.clothing_catalog(db, uid, text); send(uid, msg, buttons); return
    if text == "🔫 Оружие":
        msg, buttons = v5.weapon_shop(); send(uid, msg, buttons); return
    if text == "💎 Премиум":
        msg, buttons = v5.premium_shop(); send(uid, msg, buttons); return
    if text == "👤 Персонаж":
        msg, buttons = v5.character(db, uid); send(uid, msg, buttons); return
    if text in ("↩️ В магазин", "🛒 В магазин"):
        msg, buttons = v5.shop_hub(); send(uid, msg, buttons); return
    if text == "↩️ К одежде":
        msg, buttons = v5.clothing_menu(); send(uid, msg, buttons); return
    item_choice = next((name for name, _ in v5.ITEMS if text.startswith(name + " — ")), None)
    if item_choice:
        msg, buttons = v5.buy_item(db, uid, item_choice); send(uid, msg, buttons); return
    if text.startswith("🗑 Продать #"):
        try:
            msg, buttons = v5.sell_item(db, uid, int(text.split("#", 1)[1])); send(uid, msg, buttons)
        except ValueError:
            send(uid, "❌ Неверный ID вещи.")
        return
    if text.startswith("🎪 "):
        title = text[3:].strip()
        for key, event in v5.EVENTS.items():
            if event["title"] == title and key in __import__("catalog").active_events():
                msg, buttons = v5.participate_event(db, uid, key)
                send_card(uid, msg, buttons)
                return

    clothing_choice = None
    for category, rows in list(v5.CLOTHING.items()) + list(v5.EVENT_CLOTHING.items()):
        for name, _, _ in rows:
            if text.endswith(name) or text.startswith("🛒 " + name) or text.startswith("✅ " + name):
                clothing_choice = (category, name); break
        if clothing_choice: break
    if clothing_choice:
        msg, buttons = v5.buy_wardrobe(db, uid, *clothing_choice); send(uid, msg, buttons); return
    weapon_choice = next((name for name, _, _ in v5.WEAPONS if text.startswith(name)), None)
    if weapon_choice:
        msg, buttons = v5.buy_weapon(db, uid, weapon_choice); send(uid, msg, buttons); return
    premium_choice = next((name for name, _, _ in v5.PREMIUM if text.startswith(name)), None)
    if premium_choice:
        msg, buttons = v5.buy_premium(db, uid, premium_choice); send(uid, msg, buttons); return

    if text == "🎟 Промокод":
        send(uid, "🎟 UNDERGROUND PASS\n\nИспользование: /promo КОД\n\nСекретные дропы появляются во время событий.", [["🏙️ Главное меню"]])
        return
    if low.startswith("/promo "):
        parts = text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            send(uid, "Использование: /promo КОД", [["🎟 Промокод"], ["🏙️ Главное меню"]])
            return
        ok, msg = db.redeem_promo(user["id"], parts[1].strip())
        send(uid, msg, [["🎟 Промокод"], ["🏙️ Главное меню"]])
        return

    if text == "🎰 Казино":
        send(uid, "🎰 КАЗИНО\n\nМинимальная ставка $10 000.", kb_casino()); return
    if text == "📊 Статистика казино":
        send(uid, game.casino_info(user["id"]), kb_casino()); return
    if text == "🎯 Миссии":
        send(uid, game.missions(user["id"]), [["💼 Рабочая смена"], ["💵 Заработок"], ["🎰 Азарт"], ["🍀 Удача"], ["💰 Капитал"], ["🤝 Связи"], ["🏙️ Главное меню"]]); return
    mission_map={"💼 Рабочая смена":"work_3","💵 Заработок":"earn_100k","🎰 Азарт":"casino_3","🍀 Удача":"casino_win","💰 Капитал":"rich","🤝 Связи":"ref_1"}
    if text in mission_map:
        send(uid, game.claim_mission(user["id"],mission_map[text]), [["🎯 Миссии"], ["🏙️ Главное меню"]]); return
    if text == "📩 СМС":
        send(uid, game.sms(user["id"]), [["💼 Первое дело","🚗 Первая машина"],["🏢 Свой бизнес"],["🏙️ Главное меню"]]); return
    sms_task_map={"💼 Первое дело":"first_job","🚗 Первая машина":"first_car","🏢 Свой бизнес":"first_business"}
    if text in sms_task_map:
        send(uid, game.complete_sms_task(user["id"],sms_task_map[text]), [["📩 СМС"],["🏙️ Главное меню"]]); return
    if text == "📖 Сюжет":
        send(uid, game.story(user["id"]), [["📖 Следующая глава"], ["🏙️ Главное меню"]]); return
    if text == "📖 Следующая глава":
        r=db.story(user["id"]); db.story_set(user["id"], min(int(r["chapter"])+1, len(game.STORY)), 0)
        send(uid, game.story(user["id"]), [["📖 Следующая глава"], ["🏙️ Главное меню"]]); return
    if text == "🎓 Обучение":
        send(uid, game.tutorial(user["id"]), [["▶️ Далее"], ["🏙️ Главное меню"]]); return
    if text == "▶️ Далее":
        send(uid, game.tutorial_next(user["id"]), [["▶️ Далее"], ["🏙️ Главное меню"]]); return
    if text == "🏆 Ачивки":
        send(uid, game.achievements_full(user["id"]), [["🏙️ Главное меню"]]); return
    if text == "📱 Телефон":
        send(uid, game.phone(user["id"]), kb_phone()); return
    if text == "👥 Контакты":
        send(uid, game.phone(user["id"]), kb_phone()); return
    if text == "➕ Добавить контакт":
        set_state(uid, "phone_add")
        send(uid, "➕ Введи VK ID игрока, которого хочешь добавить в телефон.", [["❌ Отмена"]]); return
    if text == "➖ Удалить контакт":
        set_state(uid, "phone_remove")
        send(uid, "➖ Введи VK ID контакта для удаления.", [["❌ Отмена"]]); return
    if text == "🤝 NPC города":
        send(uid, game.npc_menu(user["id"]), kb_npc()); return
    npc_map={"💰 Дилер":"dealer","🕴️ Фиксер":"fixer","🔧 Механик":"mechanic","🕵️ Информатор":"informant"}
    if text in npc_map:
        code = npc_map[text]
        send(uid, game.npc(user["id"], code), kb_npc(code)); return
    npc_action_map = {label: code for code, label in NPC_ACTION_BUTTONS.items()}
    if text in npc_action_map:
        code = npc_action_map[text]
        send(uid, game.npc_action(user["id"], code), kb_npc(code)); return
    if text in ("🎲 Кости", "🎰 Слоты", "🎯 Рулетка", "🃏 Blackjack"):
        send(uid, game.casino(user["id"], text), kb_casino()); return

    if text == "🏦 Банк":
        u = db.user(user["id"])
        send(uid, f"🏦 БАНК\n\n💵 Наличные: {money(u['balance'])}\n🏦 На счёте: {money(u['bank'])}\n\nВыбери операцию:", kb_bank()); return
    if text == "💵 Положить $10k": send(uid, game.bank(user["id"], "deposit", 10_000), kb_bank()); return
    if text == "💸 Снять $10k": send(uid, game.bank(user["id"], "withdraw", 10_000), kb_bank()); return
    if text == "💵 Внести сумму": set_state(uid, "bank_in"); send(uid, "💵 Введи сумму для пополнения банка:\n\nПример: 37500", [["❌ Отмена"]]); return
    if text == "💸 Снять сумму": set_state(uid, "bank_out"); send(uid, "💸 Введи сумму для снятия из банка:\n\nПример: 37500", [["❌ Отмена"]]); return
    if low.startswith("/bank "):
        try:
            p = text.split()
            if len(p) != 3 or p[1] not in ("in", "deposit", "out", "withdraw"):
                raise ValueError
            action = "deposit" if p[1] in ("in", "deposit") else "withdraw"
            amount = int(p[2].replace(" ", ""))
            if amount <= 0:
                raise ValueError
            send(uid, game.bank(user["id"], action, amount), kb_bank())
        except (ValueError, IndexError):
            send(uid, "Использование: /bank in SUM или /bank out SUM", kb_bank())
        return
    if text == "🎁 Бонус" or low == "/daily": send(uid, game.daily(user["id"]), main_kb(uid)); return
    if text == "🏆 Достижения" or low == "/achievements": send(uid, game.achievements(user["id"]), main_kb(uid)); return

    if text == "👥 Игроки":
        send(uid, "👥 ИГРОКИ\n\n💸 Перевод — отправь VK ID и сумму\n/scam VK_ID — скам\n/rob VK_ID — ограбление\n/ref — реферальная ссылка\n/top — рейтинг", [["💸 Перевод", "/ref"], ["🏆 Рейтинг", "🏙️ Главное меню"]]); return
    if text == "💸 Перевод": set_state(uid, "pay"); send(uid, "💸 Введи двумя числами: VK_ID СУММА\n\nПример: 123456789 37500", [["❌ Отмена"]]); return
    if low == "/ref": send(uid, game.ref_link(user["id"]), main_kb(uid)); return
    if low == "/top" or text == "🏆 Рейтинг": send(uid, game.top(), main_kb(uid)); return
    if low.startswith("/pay "):
        try:
            p = text.split(); send(uid, game.transfer(user["id"], int(p[1]), int(p[2])), main_kb(uid))
        except (ValueError, IndexError): send(uid, "Использование: /pay VK_ID SUM", main_kb(uid))
        return
    if low.startswith("/scam ") or low.startswith("/rob "):
        try:
            p = text.split(); send(uid, game.attack(user["id"], int(p[1]), "scam" if low.startswith("/scam") else "rob"), main_kb(uid))
        except (ValueError, IndexError): send(uid, "Использование: /scam VK_ID или /rob VK_ID", main_kb(uid))
        return

    if role_ui.main_button(uid):
        if text in ("👑 Центр владельца", "⚙️ Панель администратора", "🛡 Панель модератора"):
            handled, response, rows = admin.handle(uid, text)
            if handled:
                if response.startswith("__BROADCAST_EXEC__|"):
                    execute_broadcast(uid, response.split("|", 1)[1]); return
                if response == "__MAIN__":
                    send_card(uid, "🏙 Главное меню", main_kb(uid)); return
                send_card(uid, response, rows); return

        handled, response, rows = admin.handle(uid, text)
        if handled:
            if response == "__MAIN__":
                send_card(uid, "🏙 Главное меню", main_kb(uid)); return
            send_card(uid, response, rows); return

    if has_admin_access(uid):
        if low.startswith("/broadcast "):
            payload = text.split(maxsplit=1)[1].strip()
            if payload:
                last = BROADCAST_LAST.get(uid, 0)
                remaining = BROADCAST_COOLDOWN - (time.time() - last)
                if remaining > 0:
                    send(uid, f"⏳ Повтори рассылку через {int(remaining) + 1} сек.", [[role_ui.main_button(uid) or "👑 Админ-панель"]])
                    return
                admin.state[uid] = ("broadcast", payload)
                send(uid, f"📢 ПРЕДПРОСМОТР РАССЫЛКИ\n\n{payload}\n\nОтправить всем игрокам?", [["✅ Отправить", "❌ Отмена"]])
            return
        if admin.state.get(uid) and isinstance(admin.state.get(uid), tuple) and admin.state[uid][0] == "broadcast":
            state = admin.state.pop(uid)
            if text == "❌ Отмена":
                send(uid, "Рассылка отменена.", [[role_ui.main_button(uid) or "👑 Админ-панель"]]); return
            if text == "✅ Отправить":
                last = BROADCAST_LAST.get(uid, 0)
                remaining = BROADCAST_COOLDOWN - (time.time() - last)
                if remaining > 0:
                    send(uid, f"⏳ Повтори рассылку через {int(remaining) + 1} сек.", [[role_ui.main_button(uid) or "👑 Админ-панель"]]); return
                execute_broadcast(uid, state[1])
                return
            admin.state[uid] = state
        handled, response, rows = admin.handle(uid, text)
        if handled:
            if response.startswith("__BROADCAST_EXEC__|"):
                execute_broadcast(uid, response.split("|", 1)[1]); return
            if response == "__MAIN__":
                send_card(uid, "🏙 Главное меню", kb_main(True)); return
            send_card(uid, response, rows); return
        if low.startswith("/admin"):
            send_card(uid, game.admin_command(user["id"], text), [["👑 Админ-панель"], ["🏙️ Главное меню"]]); return

    if text in ("◀️ Назад", "🏙️ Главное меню"):
        send_card(uid, "🏙 Главное меню", main_kb(uid)); return
    send(uid, "🤔 Неизвестная команда. Нажми «❓ Помощь» или /menu.", main_kb(uid))


def business_worker():
    while True:
        try: db.tick_all_businesses()
        except Exception: logging.exception("Ошибка фонового тика бизнеса")
        time.sleep(60)


def main():
    # Release announcements run in the background so Long Poll starts immediately.
    threading.Thread(
        target=lambda: announce_new_release(db, vk, GROUP_ID),
        name="release-announcement",
        daemon=True,
    ).start()
    threading.Thread(target=business_worker, daemon=True).start()
    logging.info("Bandit City запущен.")
    for event in longpoll.listen():
        try:
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                process(event.user_id, event.text or "")
        except Exception: logging.exception("Ошибка обработки сообщения")


if __name__ == "__main__": main()