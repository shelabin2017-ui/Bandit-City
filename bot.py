import logging
import os
import random
import threading
import time
from pathlib import Path

import requests

from dotenv import load_dotenv
import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType

from db import Database
from game import Game
from v5 import bridge as v5

load_dotenv()

TOKEN = os.getenv("VK_TOKEN", "").strip()
GROUP_ID = int(os.getenv("GROUP_ID", "0") or 0)
ADMIN_IDS = {
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

if not TOKEN or not GROUP_ID:
    raise SystemExit("Заполни VK_TOKEN и GROUP_ID в .env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

db = Database(os.getenv("DB_PATH", "bandit.db"))
game = Game(db, ADMIN_IDS)

session = vk_api.VkApi(token=TOKEN)
vk = session.get_api()
longpoll = VkLongPoll(session)


CARD_CACHE = {}
CARD_DIR = Path(__file__).resolve().parent / "assets" / "cards"

def send(user_id, text, keyboard=None, attachment=None):
    payload = {
        "user_id": user_id,
        "random_id": random.randint(1, 2_147_483_647),
        "message": text,
    }
    if keyboard:
        payload["keyboard"] = keyboard.get_keyboard()
    if attachment:
        payload["attachment"] = attachment
    vk.messages.send(**payload)


def card_key(text):
    t=text.lower()
    if "магазин" in t or "black market" in t or "одежд" in t or "оруж" in t:
        return "shop"
    if "профил" in t or "story" in t:
        return "profile"
    if "гараж" in t or "авто" in t or "машин" in t:
        return "garage"
    if "промокод" in t or "promo" in t or "under" in t:
        return "promo"
    return "main"


def upload_card(user_id, key):
    if key in CARD_CACHE:
        return CARD_CACHE[key]
    try:
        import cairosvg
        svg=CARD_DIR / (key + ".svg")
        png=CARD_DIR / (key + ".png")
        if not png.exists() or png.stat().st_mtime < svg.stat().st_mtime:
            cairosvg.svg2png(url=str(svg), write_to=str(png), output_width=1200, output_height=630)
        upload=vk.photos.getMessagesUploadServer(peer_id=user_id)
        with png.open("rb") as fh:
            response=requests.post(upload["upload_url"], files={"photo": fh}, timeout=30).json()
        saved=vk.photos.saveMessagesPhoto(
            server=response["server"], photo=response["photo"], hash=response["hash"]
        )
        photo=saved[0]
        attachment=f"photo{photo['owner_id']}_{photo['id']}"
        CARD_CACHE[key]=attachment
        return attachment
    except Exception:
        logging.exception("Не удалось загрузить визуальную карточку %s", key)
        return None


def button_color(label):
    if any(x in label for x in ("Назад", "В магазин", "К одежде", "Главное меню")):
        return VkKeyboardColor.SECONDARY
    if any(x in label for x in ("Купить", "Куплено", "Активировать", "Промокод", "Бонус")):
        return VkKeyboardColor.POSITIVE
    if any(x in label for x in ("Продать", "Удалить", "Казино", "Риск")):
        return VkKeyboardColor.NEGATIVE
    return VkKeyboardColor.PRIMARY


def send_v5(user_id, text, rows):
    keyboard = VkKeyboard(one_time=False)
    for row in rows:
        if isinstance(row, str):
            row=[row]
        for index, label in enumerate(row):
            keyboard.add_button(str(label)[:40], button_color(str(label)))
            if index < len(row)-1:
                pass
        keyboard.add_line()
    attachment=upload_card(user_id, card_key(text))
    send(user_id, text, keyboard, attachment)

def kb_main():
    k = VkKeyboard(one_time=False)
    rows = [
        [("👤 Профиль", VkKeyboardColor.PRIMARY), ("💼 Работа", VkKeyboardColor.POSITIVE)],
        [("🚗 Авто", VkKeyboardColor.PRIMARY), ("🛒 Магазин", VkKeyboardColor.PRIMARY)],
        [("🏢 Бизнес", VkKeyboardColor.PRIMARY), ("🏦 Банк", VkKeyboardColor.PRIMARY)],
        [("🎰 Казино", VkKeyboardColor.NEGATIVE), ("🎁 Бонус", VkKeyboardColor.POSITIVE)],
        [("👥 Игроки", VkKeyboardColor.PRIMARY), ("🏆 Рейтинг", VkKeyboardColor.PRIMARY)],
        [("🏆 Достижения", VkKeyboardColor.PRIMARY), ("🎟 Промокод", VkKeyboardColor.POSITIVE)],
    ]
    for row in rows:
        for i,(label,color) in enumerate(row):
            k.add_button(label,color)
            if i < len(row)-1:
                pass
        k.add_line()
    return k


def kb_bank():
    k = VkKeyboard(one_time=False)
    k.add_button("💵 Положить $10k", VkKeyboardColor.PRIMARY)
    k.add_button("💸 Снять $10k", VkKeyboardColor.POSITIVE)
    k.add_line()
    k.add_button("◀️ Назад", VkKeyboardColor.SECONDARY)
    return k


def kb_work():
    k = VkKeyboard(one_time=False)
    for label in ("🚕 Таксист", "🕵️ Федерал", "📦 Блок", "🔗 Рефка"):
        k.add_button(label, VkKeyboardColor.PRIMARY)
        if label in ("🚕 Таксист", "📦 Блок"):
            k.add_line()
    k.add_button("◀️ Назад", VkKeyboardColor.SECONDARY)
    return k


def kb_business():
    k = VkKeyboard(one_time=False)
    k.add_button("🏭 Купить аэропорт", VkKeyboardColor.POSITIVE)
    k.add_button("📦 Склад", VkKeyboardColor.PRIMARY)
    k.add_line()
    k.add_button("💰 Снять деньги", VkKeyboardColor.POSITIVE)
    k.add_button("ℹ️ Инфо", VkKeyboardColor.PRIMARY)
    k.add_line()
    k.add_button("◀️ Назад", VkKeyboardColor.SECONDARY)
    return k


def kb_auto():
    k = VkKeyboard(one_time=False)
    k.add_button("🚙 Обычные", VkKeyboardColor.PRIMARY)
    k.add_button("🏎 Спорт", VkKeyboardColor.PRIMARY)
    k.add_line()
    k.add_button("🔥 Суперкары", VkKeyboardColor.PRIMARY)
    k.add_button("💿 Лоурайдеры", VkKeyboardColor.PRIMARY)
    k.add_line()
    k.add_button("🚘 Гараж", VkKeyboardColor.PRIMARY)
    k.add_button("◀️ Назад", VkKeyboardColor.SECONDARY)
    return k


def kb_shop():
    k = VkKeyboard(one_time=False)
    k.add_button("💻 MacBook", VkKeyboardColor.PRIMARY)
    k.add_button("👟 Кроссовки", VkKeyboardColor.PRIMARY)
    k.add_line()
    k.add_button("👕 Куртка", VkKeyboardColor.PRIMARY)
    k.add_button("💇 Волосы", VkKeyboardColor.PRIMARY)
    k.add_line()
    k.add_button("📦 Мои вещи", VkKeyboardColor.PRIMARY)
    k.add_button("◀️ Назад", VkKeyboardColor.SECONDARY)
    return k


def kb_casino():
    k = VkKeyboard(one_time=False)
    k.add_button("🎲 Кости", VkKeyboardColor.NEGATIVE)
    k.add_button("🎰 Слоты", VkKeyboardColor.NEGATIVE)
    k.add_line()
    k.add_button("🎯 Рулетка", VkKeyboardColor.NEGATIVE)
    k.add_button("🃏 Blackjack", VkKeyboardColor.NEGATIVE)
    k.add_line()
    k.add_button("◀️ Назад", VkKeyboardColor.SECONDARY)
    return k


def money(n):
    return f"${int(n):,}".replace(",", " ")


def process(uid, text):
    if v5.MAINTENANCE and uid not in v5.ADMIN_IDS:
        send(uid, "🔧 ТЕХНИЧЕСКИЕ РАБОТЫ\n\nБот временно недоступен.\nПожалуйста, зайди немного позже.")
        return

    if db.is_banned(uid):
        send(uid, "⛔ Твой аккаунт заблокирован.")
        return

    user = db.get_or_create_user(uid)
    text = text.strip()
    low = text.lower()

    # Первый вход / регистрация
    if db.needs_onboarding(user["id"]):
        referral_bonus = False
        if low.startswith("/start"):
            parts = text.split(maxsplit=1)
            if len(parts) == 2:
                referral_bonus = bool(game.apply_referral(user["id"], parts[1]))
        db.complete_onboarding(user["id"])
        send(uid, game.welcome(user["id"], referral_bonus), kb_main())
        return

    # Повторный /start просто открывает профиль
    if low.startswith("/start"):
        send(uid, game.profile(user["id"]), kb_main())
        return

    if low in ("/menu", "меню"):
        send(uid, "🏙 Главное меню", kb_main())
        return

    if low in ("/info", "инфо", "👤 профиль"):
        send(uid, game.profile(user["id"]), kb_main())
        return

    # Work
    if text == "💼 Работа":
        send(uid, "💼 ВЫБЕРИ РАБОТУ", kb_work())
        return
    work_map = {"🚕 Таксист":"taxi", "🕵️ Федерал":"federal", "📦 Блок":"block", "🔗 Рефка":"refwork"}
    if text in work_map:
        send(uid, game.work(user["id"], work_map[text]), kb_work())
        return

    # Business
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
    if low.startswith("/stock "):
        try:
            amount = int(text.split()[1])
            send(uid, game.refill_stock(user["id"], amount), kb_business())
        except (ValueError, IndexError):
            send(uid, "Использование: /stock КОЛИЧЕСТВО", kb_business())
        return

    # Cars
    if text == "🚗 Авто":
        send(uid, "🚗 АВТОСАЛОН", kb_auto())
        return
    cats = {"🚙 Обычные":"common", "🏎 Спорт":"sport", "🔥 Суперкары":"super", "💿 Лоурайдеры":"lowrider", "🚘 Спецтранспорт":"special"}
    if text in cats:
        send(uid, game.catalog(cats[text]), kb_auto())
        return
    if text == "🚘 Гараж" or low == "/garage":
        send(uid, game.garage(user["id"]), kb_auto())
        return
    if low.startswith("/buycar "):
        send(uid, game.buy_car(user["id"], text.split(maxsplit=1)[1]), kb_auto())
        return
    if low.startswith("/sellcar "):
        try:
            send(uid, game.sell_car(user["id"], int(text.split()[1])), kb_auto())
        except (ValueError, IndexError):
            send(uid, "Использование: /sellcar ID", kb_auto())
        return

    # V5 Shop / Inventory / Wardrobe / Character
    if text == "🛒 Магазин":
        msg, buttons = v5.shop_hub()
        send_v5(uid, msg, buttons)
        for row in buttons:
            pass
        return

    if text == "🛍️ Предметы":
        msg, buttons = v5.item_shop()
        send_v5(uid, msg, buttons)
        return
    if text == "🎒 Инвентарь":
        msg, buttons = v5.inventory(db, uid)
        send_v5(uid, msg, buttons)
        return
    if text == "🧥 Одежда":
        msg, buttons = v5.clothing_menu()
        send_v5(uid, msg, buttons)
        return
    if text in v5.CLOTHING:
        msg, buttons = v5.clothing_catalog(db, uid, text)
        send_v5(uid, msg, buttons)
        return
    if text == "🔫 Оружие":
        msg, buttons = v5.weapon_shop()
        send_v5(uid, msg, buttons)
        return
    if text == "💎 Премиум":
        msg, buttons = v5.premium_shop()
        send_v5(uid, msg, buttons)
        return
    if text == "🚗 Авто":
        msg, buttons = v5.car_dealership()
        send_v5(uid, msg, buttons)
        return
    if text == "👤 Персонаж":
        msg, buttons = v5.character(db, uid)
        send_v5(uid, msg, buttons)
        return

    item_choice = next((name for name, _price in v5.ITEMS if text.startswith(name + " — ")), None)
    if item_choice:
        msg, buttons = v5.buy_item(db, uid, item_choice)
        send_v5(uid, msg, buttons)
        return

    if text.startswith("🗑 Продать #"):
        try:
            item_id = int(text.split("#", 1)[1])
            msg, buttons = v5.sell_item(db, uid, item_id)
            send_v5(uid, msg, buttons)
        except ValueError:
            send(uid, "❌ Неверный ID вещи.")
        return

    clothing_choice = None
    for category, rows in v5.CLOTHING.items():
        for name, _price, _slot in rows:
            if text.endswith(name) or text.startswith("🛒 " + name) or text.startswith("✅ " + name):
                clothing_choice = (category, name)
                break
        if clothing_choice:
            break
    if clothing_choice:
        msg, buttons = v5.buy_wardrobe(db, uid, *clothing_choice)
        send_v5(uid, msg, buttons)
        return

    weapon_choice = next((name for name, _price, _code in v5.WEAPONS if text.startswith(name)), None)
    if weapon_choice:
        msg, buttons = v5.buy_weapon(db, uid, weapon_choice)
        send_v5(uid, msg, buttons)
        return

    premium_choice = next((name for name, _price, _code in v5.PREMIUM if text.startswith(name)), None)
    if premium_choice:
        msg, buttons = v5.buy_premium(db, uid, premium_choice)
        send_v5(uid, msg, buttons)
        return

    if text in ("↩️ В магазин", "🛒 В магазин"):
        msg, buttons = v5.shop_hub()
        send_v5(uid, msg, buttons)
        return
    if text == "↩️ К одежде":
        msg, buttons = v5.clothing_menu()
        send_v5(uid, msg, buttons)
        return

    if text == "🎟 Промокод":
        send_v5(uid,
                "🎟 UNDERGROUND PASS\n\n"
                "Одноразовые промокоды дают уникальные награды.\n"
                "Использование: /promo КОД\n\n"
                "Некоторые коды выдаются только владельцам проекта, "
                "на закрытых ивентах и в специальных дропах.",
                [["🏙️ Главное меню"]])
        return
    if low.startswith("/promo "):
        code=text.split(maxsplit=1)[1].strip()
        ok,msg=db.redeem_promo(user["id"],code)
        send_v5(uid,msg,[["🎟 Промокод"],["🏙️ Главное меню"]])
        return

    # Casino
    if text == "🎰 Казино":
        send(uid, "🎰 КАЗИНО\nМинимальная ставка $10 000.", kb_casino())
        return
    if text in ("🎲 Кости", "🎰 Слоты", "🎯 Рулетка", "🃏 Blackjack"):
        send(uid, game.casino(user["id"], text), kb_casino())
        return

    # Bank / bonuses / achievements
    if text == "🏦 Банк":
        u = db.user(user["id"])
        send(uid, f"🏦 БАНК\n\n💵 Наличные: {money(u['balance'])}\n🏦 На счёте: {money(u['bank'])}\n\nБыстрые операции по $10 000:", kb_bank())
        return
    if text == "💵 Положить $10k":
        send(uid, game.bank(user["id"], "deposit", 10_000), kb_bank())
        return
    if text == "💸 Снять $10k":
        send(uid, game.bank(user["id"], "withdraw", 10_000), kb_bank())
        return
    if text == "🎁 Бонус":
        send(uid, game.daily(user["id"]), kb_main())
        return
    if text == "🏆 Достижения":
        send(uid, game.achievements(user["id"]), kb_main())
        return
    if low.startswith("/bank "):
        try:
            p = text.split(); action = p[1]; amount = int(p[2])
            send(uid, game.bank(user["id"], "deposit" if action in ("in","deposit") else "withdraw", amount), kb_bank())
        except (ValueError, IndexError):
            send(uid, "Использование: /bank in СУММА или /bank out СУММА", kb_bank())
        return
    if low == "/daily":
        send(uid, game.daily(user["id"]), kb_main())
        return
    if low == "/achievements":
        send(uid, game.achievements(user["id"]), kb_main())
        return

    # Players
    if text == "👥 Игроки":
        send(uid,
             "👥 ИГРОКИ\n\n"
             "/pay VK_ID СУММА — перевод\n"
             "/scam VK_ID — скам\n"
             "/rob VK_ID — ограбление\n"
             "/ref — реферальная ссылка\n"
             "/top — рейтинг",
             kb_main())
        return
    if low == "/ref":
        send(uid, game.ref_link(user["id"]), kb_main())
        return
    if low == "/top" or text == "🏆 Рейтинг":
        send(uid, game.top(), kb_main())
        return
    if low.startswith("/pay "):
        try:
            p = text.split()
            send(uid, game.transfer(user["id"], int(p[1]), int(p[2])), kb_main())
        except (ValueError, IndexError):
            send(uid, "Использование: /pay VK_ID СУММА", kb_main())
        return
    if low.startswith("/scam ") or low.startswith("/rob "):
        try:
            p = text.split()
            mode = "scam" if low.startswith("/scam ") else "rob"
            send(uid, game.attack(user["id"], int(p[1]), mode), kb_main())
        except (ValueError, IndexError):
            send(uid, "Использование: /scam VK_ID или /rob VK_ID", kb_main())
        return

    # Admin
    if uid in ADMIN_IDS and text == "👑 Админка":
        send(uid, game.admin_command(user["id"], "/admin"), kb_main())
        return
    if uid in ADMIN_IDS and low.startswith("/admin"):
        send(uid, game.admin_command(user["id"], text), kb_main())
        return

    if text == "◀️ Назад":
        send(uid, "🏙 Главное меню", kb_main())
        return

    send(uid, "🤔 Неизвестная команда. Используй /menu.", kb_main())


def business_worker():
    while True:
        try:
            db.tick_all_businesses()
        except Exception:
            logging.exception("Ошибка фонового тика бизнеса")
        time.sleep(60)


def main():
    threading.Thread(target=business_worker, daemon=True).start()
    logging.info("Bandit City запущен.")
    for event in longpoll.listen():
        try:
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                process(event.user_id, event.text)
        except Exception:
            logging.exception("Ошибка обработки сообщения")


if __name__ == "__main__":
    main()
