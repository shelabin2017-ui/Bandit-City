"""V5 shop layer. Public catalogue is separated from event-only drops."""
import random
import time
from catalog import EVENTS, EVENT_EXCLUSIVES, active_events, find_event_item

MAINTENANCE = False
ADMIN_IDS = set()

ITEMS = [
    ("💻 MacBook", 120000), ("👟 Кроссовки", 25000), ("👕 Куртка", 45000),
    ("💇 Волосы", 30000), ("📱 Burner Phone", 65000), ("🧰 Набор отмычек", 85000),
    ("🩹 Аптечка", 30000), ("⚡ Энергетик", 15000), ("🎭 Маска", 45000),
    ("🛡 Бронежилет", 180000), ("🧰 Инструменты", 95000), ("🍀 Счастливый жетон", 125000),
    ("🍔 Бургер", 12000), ("🥪 Сэндвич", 8000), ("💧 Вода", 3000),
    ("🎁 Подарочный бокс", 200000),
]

CLOTHING = {
    "🧢 Головные уборы": [("🧢 Чёрная кепка",8000,"head"),("🎩 Классическая шляпа",15000,"head"),("🪖 Тактический шлем",35000,"head"),("🤠 Ковбойская шляпа",22000,"head")],
    "👕 Верх": [("👕 Белая футболка",12000,"clothes"),("🧥 Кожаная куртка",45000,"clothes"),("🧥 Бомбер",38000,"clothes"),("👔 Чёрный пиджак",60000,"clothes"),("🥋 Спортивная кофта",28000,"clothes")],
    "👖 Брюки": [("👖 Джинсы",18000,"pants"),("👖 Чёрные джинсы",24000,"pants"),("🩳 Шорты",14000,"pants"),("👔 Классические брюки",32000,"pants")],
    "🥾 Обувь": [("👟 Кроссовки",25000,"shoes"),("🥾 Тактические ботинки",32000,"shoes"),("👞 Классические туфли",40000,"shoes"),("👢 Высокие ботинки",45000,"shoes")],
    "💍 Аксессуары": [("🕶 Чёрные очки",12000,"accessory"),("⌚ Золотые часы",55000,"accessory"),("💎 Цепь",75000,"accessory"),("🎧 Наушники",30000,"accessory")],
    "💇 Волосы": [("💇 Короткая стрижка",20000,"hair"),("💇 Длинная стрижка",28000,"hair"),("💈 Fade",35000,"hair"),("💈 Undercut",42000,"hair")],
}

# Never mix these with CLOTHING. They are not purchasable in the normal shop.
EVENT_CLOTHING = {
    "🎪 Ивент • Эксклюзивы": [
        ("🖤 Shadow Jacket",0,"clothes"),("🌌 Neon Shades",0,"accessory"),("👑 Prime Hair",0,"hair"),
        ("🧥 Founder Jacket",0,"clothes"),("🎭 Nightfall Mask",0,"head"),("⛓ Blackout Chain",0,"accessory"),
        ("🏆 Bandit Legend Outfit",0,"clothes"),("🌃 Neon City Background",0,"background"),("🔫 Golden Bullet",0,"accessory"),
    ]
}

# Расширенный игровой каталог. Оружие является внутриигровым предметом;
# цены и коды стабильны, чтобы покупки корректно сохранялись в v5_weapons.
WEAPONS = [
    ("🔪 Нож", 15000, "knife"),
    ("🪓 Тактический топор", 28000, "tactical_axe"),
    ("🗡️ Боевой кинжал", 35000, "combat_dagger"),
    ("🏏 Бита", 12000, "baseball_bat"),
    ("🔧 Тяжёлый лом", 9000, "crowbar"),
    ("🔫 Пистолет", 75000, "pistol"),
    ("🔫 Компактный пистолет", 62000, "compact_pistol"),
    ("🔫 Desert Eagle", 180000, "deagle"),
    ("🔫 Револьвер", 115000, "revolver"),
    ("🔫 Тактический пистолет", 145000, "tactical_pistol"),
    ("🔫 Дробовик", 250000, "shotgun"),
    ("🔫 Помповый дробовик", 285000, "pump_shotgun"),
    ("🔫 Обрез", 190000, "sawed_off"),
    ("🔫 Автоматический дробовик", 420000, "auto_shotgun"),
    ("🔫 SMG", 350000, "smg"),
    ("🔫 Компактный SMG", 310000, "compact_smg"),
    ("🔫 Тактический SMG", 460000, "tactical_smg"),
    ("🔫 Vector-9", 520000, "vector9"),
    ("🔫 Карабин", 480000, "carbine"),
    ("🔫 Штурмовой карабин", 620000, "assault_carbine"),
    ("🔫 Тактическая винтовка", 700000, "tactical_rifle"),
    ("🔫 Булл-пап", 760000, "bullpup"),
    ("🎯 Охотничья винтовка", 540000, "hunting_rifle"),
    ("🎯 Снайперская винтовка", 950000, "sniper_rifle"),
    ("🎯 Точная винтовка", 880000, "marksman_rifle"),
    ("🔫 Лёгкий пулемёт", 1100000, "light_machine_gun"),
    ("🔫 Тяжёлый пулемёт", 1450000, "heavy_machine_gun"),
    ("🏹 Арбалет", 160000, "crossbow"),
    ("💣 Дымовая граната", 45000, "smoke_grenade"),
    ("💥 Светошумовая граната", 55000, "flash_grenade"),
    ("🛡️ Электрошокер", 68000, "stun_gun"),
    ("🎯 Тренировочный пистолет", 25000, "training_pistol"),
    ("🔫 Киберпанк-бластер", 1250000, "cyber_blaster"),
    ("🔫 Неоновый SMG", 980000, "neon_smg"),
    ("🔫 Золотой Desert Eagle", 1750000, "gold_deagle"),
    ("🔫 Чёрный тактический карабин", 1350000, "black_carbine"),
    ("🔫 Прототип X-9", 2200000, "prototype_x9"),
    ("🔫 Легендарный «Фантом»", 3500000, "phantom_legend"),
]
PREMIUM = [("💎 VIP-карточка",500000,"vip"),("⚡ Буст XP x2",250000,"xp_boost"),("🎟 Премиум-пропуск",750000,"pass")]

def money(n): return "$" + f"{int(n):,}".replace(","," ")
def reply(text,buttons=None): return text, buttons or []
def player_id_by_vk(db,vk_id):
    row=db.get_or_create_user(vk_id); return row["id"] if row else None
def _conn(db): return db.connect()
def _owned(db,user_id,category,name):
    with _conn(db) as c: return bool(c.execute("SELECT 1 FROM v5_wardrobe WHERE user_id=? AND category=? AND name=?",(user_id,category,name)).fetchone())

def shop_hub():
    return reply("🛒 МАГАЗИН LOS SANTOS\n\nВыбери раздел:",[["🧥 Одежда","🔫 Оружие"],["🚗 Авто","💎 Премиум"],["🛍️ Предметы"],["🎒 Инвентарь"],["🎪 Ивент-дропы"],["🏙️ Главное меню"]])
ITEM_CATEGORIES = {
    "🍔 Еда и напитки": ("🍔", ("бургер", "сэндвич", "вода", "энергетик")),
    "🩹 Медицина": ("🩹", ("аптечка",)),
    "🛠️ Инструменты и снаряжение": ("🛠️", ("отмычек", "инструменты", "бронежилет", "маска")),
    "👕 Одежда и аксессуары": ("👕", ("кроссовки", "куртка", "волосы")),
    "📱 Электроника": ("📱", ("macbook", "burner phone")),
    "🎁 Прочее": ("🎁", ("счастливый жетон", "подарочный бокс")),
}

def item_category(name):
    lowered = str(name).lower()
    for category, (_, words) in ITEM_CATEGORIES.items():
        if any(word in lowered for word in words):
            return category
    return "🎁 Прочее"

def item_shop(category=None):
    if not category:
        body = ["🛒 ПРЕДМЕТЫ LOS SANTOS", "", "Выбери категорию товаров:"]
        buttons = [[name] for name in ITEM_CATEGORIES]
        buttons += [["📦 Все предметы"], ["🎒 Инвентарь"], ["↩️ В магазин"], ["🏙️ Главное меню"]]
        return reply("\n".join(body), buttons)
    if category == "📦 Все предметы":
        category = None
    chosen = [(name, price) for name, price in ITEMS if category is None or item_category(name) == category]
    title = category or "📦 Все предметы"
    body = ["🛒 " + title.upper(), "", "Выбирай количество — покупка оформляется одним нажатием.", "Доступно: x1, x5, x10."]
    buttons = []
    for name, price in chosen:
        body += ["", name, "💵 За штуку: " + money(price)]
        buttons.append(["🛒 x1 " + name, "🛒 x5 " + name])
        buttons.append(["🛒 x10 " + name])
    buttons += [["↩️ К категориям"], ["🎒 Инвентарь"], ["↩️ В магазин"], ["🏙️ Главное меню"]]
    return reply("\n".join(body), buttons)

def buy_item_quantity(db, vk_id, name, quantity):
    match = next((x for x in ITEMS if x[0] == name), None)
    if not match:
        return reply("❌ Предмет отсутствует в каталоге.", [["🛍️ Предметы"], ["🛒 Магазин"]])
    quantity = int(quantity)
    if quantity < 1 or quantity > 100:
        return reply("❌ За одну покупку можно приобрести от 1 до 100 единиц.", [["🛍️ Предметы"], ["🛒 Магазин"]])
    item, price = match
    uid = player_id_by_vk(db, vk_id)
    user = db.user(uid)
    total = price * quantity
    if not user or int(user["balance"]) < total:
        return reply("❌ Недостаточно денег.\n\n" + item + "\nКоличество: " + str(quantity) + "\nИтого: " + money(total), [["🛍️ Предметы"], ["🛒 Магазин"]])
    # The balance is checked for the whole basket before writing any item.
    with _conn(db) as c:
        current = c.execute("SELECT balance FROM users WHERE id=?", (uid,)).fetchone()
        if not current or int(current["balance"]) < total:
            return reply("❌ Баланс изменился: денег на всю покупку не хватает.", [["🛍️ Предметы"], ["🛒 Магазин"]])
        c.execute("UPDATE users SET balance=balance-? WHERE id=?", (total, uid))
        now = int(time.time())
        c.executemany(
            "INSERT INTO items(user_id,name,price,bought_at) VALUES(?,?,?,?)",
            [(uid, item, price, now) for _ in range(quantity)]
        )
    return reply("✅ ПОКУПКА ОФОРМЛЕНА\n\n" + item + "\n📦 Количество: " + str(quantity) + "\n💵 За штуку: " + money(price) + "\n💰 Итого: " + money(total), [["🎒 Инвентарь"], ["🛍️ Предметы"], ["🛒 Магазин"]])

def inventory(db,vk_id):
    uid=player_id_by_vk(db,vk_id); rows=db.items(uid)
    if not rows: return reply("🎒 ИНВЕНТАРЬ LOS SANTOS\n\nКарман пуст.",[["🛒 Магазин"],["🏙️ Главное меню"]])
    body=["🎒 ИНВЕНТАРЬ LOS SANTOS",""]; buttons=[]; sell_buttons=[]
    for row in rows:
        body += ["📦 "+row["name"],"💵 Цена: "+money(row["price"]),""]
        sell_buttons.append("🗑 Продать #"+str(row["id"]))
        if str(row["name"]) == "🎁 Подарочный бокс":
            sell_buttons.append("🎁 Открыть #" + str(row["id"]))
        if any(word in str(row["name"]).lower() for word in ("бургер","сэндвич","вода","энергетик","еда","кофе")):
            sell_buttons.append("🍔 Использовать #"+str(row["id"]))
    # Never truncate inventory actions locally. send() applies the shared VK
    # arrow-pagination helper and keeps the final navigation row available.
    for i in range(0, len(sell_buttons), 2):
        buttons.append(sell_buttons[i:i + 2])
    buttons += [["🛒 Магазин"],["🏙️ Главное меню"]]
    return reply("\n".join(body),buttons)
def clothing_menu():
    return reply("🧥 ОДЕЖДА LOS SANTOS\n\nПостоянные категории. Эксклюзивы выдаются отдельно.",[["🧢 Головные уборы","👕 Верх"],["👖 Брюки","🥾 Обувь"],["💍 Аксессуары","💇 Волосы"],["↩️ В магазин"],["👤 Персонаж","🏙️ Главное меню"]])
def event_catalog(db=None,vk_id=None):
    active=active_events()
    uid=player_id_by_vk(db,vk_id) if db is not None and vk_id is not None else None
    body=["🎪 ИВЕНТ-ДРОПЫ","","🔒 Не продаются за обычные деньги.","Участие сохраняется в профиле игрока.", ""]
    buttons=[]
    for key,event in EVENTS.items():
        is_active=key in active
        state="🟢 АКТИВЕН" if is_active else "⚪ ЗАКРЫТ"
        body += [f"📅 {event['title']} • {state}",event['description']]
        if is_active and event.get("goal_code") and uid is not None:
            row=db.mission_rows(uid,[event["goal_code"]]).get(event["goal_code"],{})
            progress=min(int(row.get("progress",0)),int(event.get("goal_target",1)))
            body.append(f"🎯 Задача: {event.get('goal_label','Выполни условие')} • {progress}/{event.get('goal_target',1)}")
        body += [f"🎁 {len(event['drops'])} эксклюзивов",""]
        if is_active: buttons.append([f"🎪 {event['title']}"])
    if not buttons: body.append("⏳ Сейчас активных ивентов нет.")
    buttons += [["↩️ В магазин"],["🏙️ Главное меню"]]
    return reply("\n".join(body),buttons)

def participate_event(db,vk_id,event_key):
    event=EVENTS.get(event_key)
    if not event or event_key not in active_events():
        return reply("⏳ Это событие сейчас недоступно.", [["🎪 Ивент-дропы"],["🏙️ Главное меню"]])
    uid=player_id_by_vk(db,vk_id)
    goal_code=event.get("goal_code")
    if goal_code:
        row=db.mission_rows(uid,[goal_code]).get(goal_code,{})
        progress=int(row.get("progress",0))
        target=int(event.get("goal_target",1))
        if progress<target:
            return reply(
                f"🎯 ИВЕНТ: {event['title']}\n\n"
                f"Задача: {event.get('goal_label','Выполни условие')}\n"
                f"Прогресс: {min(progress,target)}/{target}\n\n"
                "Награда откроется после выполнения условия. Прогресс засчитывается автоматически.",
                [["🎪 Ивент-дропы"],["🏙️ Главное меню"]]
            )
    created,_=db.event_participation(uid,event_key)
    if not created:
        history=db.event_history(uid)
        return reply(
            "🏆 ТЫ УЖЕ УЧАСТВОВАЛ\n\n"
            f"🎪 {event['title']}\n"
            "✅ Участие сохранено в твоей истории.\n"
            "🎟 Награда уже получена.",
            [["🎪 Ивент-дропы"],["👤 Профиль"],["🏙️ Главное меню"]]
        )
    rewards=[]
    for item_id in event.get("drops",[]):
        item=find_event_item(item_id)
        if not item:
            continue
        category="🎪 Ивент • Эксклюзивы"
        name=item["name"]
        slot=item.get("slot","accessory")
        with _conn(db) as c:
            c.execute(
                "INSERT OR IGNORE INTO v5_wardrobe(user_id,category,name,price,bought_at) VALUES(?,?,?,?,?)",
                (uid,category,name,0,int(time.time()))
            )
        db.set_appearance(uid, **{slot:name})
        rewards.append(name)
    db.event_reward_claimed(uid,event_key)
    reward_text="\n".join("🎁 "+x for x in rewards) if rewards else "🎁 Награда будет объявлена позже."
    return reply(
        "🌙 НОЧНОЙ ЗАБЕГ\n\n"
        "🏆 УЧАСТИЕ ЗАСЧИТАНО\n"
        "Твой профиль отмечен как участник события.\n\n"
        f"{reward_text}\n\n"
        "🌙 Добро пожаловать в ночной город.",
        [["👤 Профиль"],["🎪 Ивент-дропы"],["🏙️ Главное меню"]]
    )

def clothing_catalog(db,vk_id,category):
    source=EVENT_CLOTHING if category in EVENT_CLOTHING else CLOTHING
    if category not in source: return clothing_menu()
    uid=player_id_by_vk(db,vk_id); body=[category.upper(),"","Каталог:"]; buttons=[]
    for name,price,slot in source[category]:
        owned=_owned(db,uid,category,name); mark="🔒" if category in EVENT_CLOTHING and not owned else ("✅" if owned else "🛒")
        body += ["",mark+" "+name,"🎟 Выдаётся через событие / промокод" if price==0 else "💵 "+money(price)]
        if price>0 or owned: buttons.append([mark+" "+name+(" — "+money(price) if price else "")])
    buttons += [["↩️ К одежде"],["🛒 В магазин","🏙️ Главное меню"]]; return reply("\n".join(body),buttons)
def weapon_shop():
    body=["🔫 ОРУЖЕЙНЫЙ МАГАЗИН","","Постоянный каталог:"]; buttons=[]
    for name,price,code in WEAPONS: body += ["",name,"💵 "+money(price)]; buttons.append([name+" — "+money(price)])
    buttons += [["↩️ В магазин"],["🏙️ Главное меню"]]; return reply("\n".join(body),buttons)
def premium_shop():
    body=["💎 ПРЕМИУМ LOS SANTOS","","Постоянный каталог:"]; buttons=[]
    for name,price,code in PREMIUM: body += ["",name,"💵 "+money(price)]; buttons.append([name+" — "+money(price)])
    buttons += [["↩️ В магазин"],["🏙️ Главное меню"]]; return reply("\n".join(body),buttons)
def car_dealership(): return reply("🚗 АВТОСАЛОН LOS SANTOS\n\nВыбери категорию:",[["🚙 Обычные","🏎 Спорт"],["🔥 Суперкары","💿 Лоурайдеры"],["🚘 Спецтранспорт"],["↩️ В магазин","🏙️ Главное меню"]])
def character(db,vk_id):
    uid=player_id_by_vk(db,vk_id); row=db.appearance(uid); labels={"hair":"💇 Волосы","clothes":"👕 Верх","pants":"👖 Брюки","shoes":"👟 Обувь","head":"🧢 Головной убор","accessory":"💍 Аксессуар","background":"🌃 Фон"}; body=["👤 ПЕРСОНАЖ",""]
    for key,label in labels.items():
        if key in row.keys(): body.append(label+": "+str(row[key]))
    return reply("\n".join(body),[["👕 Одежда","🧢 Головной убор"],["💇 Волосы","💍 Аксессуары"],["👖 Брюки","🥾 Обувь"],["🏙️ Главное меню"]])
def buy_item(db,vk_id,name):
    match=next((x for x in ITEMS if x[0]==name),None)
    if not match:return reply("❌ Предмет отсутствует в каталоге.",[["🛒 Магазин"]])
    item,price=match; uid=player_id_by_vk(db,vk_id); user=db.user(uid)
    if not user or user["balance"]<price:return reply("❌ Недостаточно денег.",[["🛒 Магазин"]])
    return reply(db.buy_item(uid,item,price),[["🎒 Инвентарь"],["🛒 Магазин"]])
def open_gift_box(db, vk_id, item_id, rng=None):
    """Consume one owned gift box and grant exactly one random reward atomically."""
    rng = rng or random
    uid = player_id_by_vk(db, vk_id)
    rewards = [
        ("cash", 25000, "💵 $25 000"),
        ("cash", 75000, "💵 $75 000"),
        ("cash", 150000, "💵 $150 000"),
        ("item", "🍔 Бургер", "🍔 Бургер"),
        ("item", "⚡ Энергетик", "⚡ Энергетик"),
        ("item", "💧 Вода", "💧 Вода"),
    ]
    with _conn(db) as c:
        row = c.execute(
            "SELECT id FROM items WHERE id=? AND user_id=? AND name=?",
            (int(item_id), uid, "🎁 Подарочный бокс"),
        ).fetchone()
        if not row:
            return reply("❌ Подарочный бокс не найден в твоём инвентаре.", [["🎒 Инвентарь"], ["🛒 Магазин"]])
        reward = rng.choice(rewards)
        deleted = c.execute(
            "DELETE FROM items WHERE id=? AND user_id=? AND name=?",
            (int(item_id), uid, "🎁 Подарочный бокс"),
        )
        if deleted.rowcount != 1:
            return reply("❌ Не удалось открыть бокс. Обнови инвентарь и попробуй снова.", [["🎒 Инвентарь"]])
        if reward[0] == "cash":
            c.execute("UPDATE users SET balance=balance+? WHERE id=?", (int(reward[1]), uid))
            description = reward[2]
        else:
            c.execute(
                "INSERT INTO items(user_id,name,price,bought_at) VALUES(?,?,?,?)",
                (uid, str(reward[1]), 0, int(time.time())),
            )
            description = reward[2]
    return reply("🎁 ПОДАРОЧНЫЙ БОКС ОТКРЫТ\n\nТебе выпало:\n" + description,
                 [["🎒 Инвентарь"], ["🛒 Магазин"], ["🏙️ Главное меню"]])

def sell_item(db,vk_id,item_id): return reply(db.sell_item(player_id_by_vk(db,vk_id),item_id),[["🎒 Инвентарь"],["🛒 Магазин"]])
def buy_wardrobe(db,vk_id,category,name):
    source=EVENT_CLOTHING if category in EVENT_CLOTHING else CLOTHING; found=next((x for x in source.get(category,[]) if x[0]==name),None)
    if not found:return reply("❌ Предмет отсутствует в каталоге.",[["🧥 Одежда"]])
    _,price,slot=found; uid=player_id_by_vk(db,vk_id)
    if category in EVENT_CLOTHING and price==0:
        if not _owned(db,uid,category,name): return reply("🔒 Нельзя купить. Получи предмет через событие или секретный промокод.",[["🎪 Ивент-дропы"],["🛒 Магазин"]])
        db.set_appearance(uid,**{slot:name}); return reply("🎟 Эксклюзив надет: "+name,[["👤 Персонаж"],["🎪 Ивент-дропы"]])
    if _owned(db,uid,category,name): db.set_appearance(uid,**{slot:name}); return reply("👕 Надето: "+name,[["👤 Персонаж"],["🧥 Одежда"]])
    user=db.user(uid)
    if not user or user["balance"]<price:return reply("❌ Недостаточно денег.",[["🧥 Одежда"]])
    with _conn(db) as c:
        c.execute("UPDATE users SET balance=balance-? WHERE id=?",(price,uid)); c.execute("INSERT OR IGNORE INTO v5_wardrobe(user_id,category,name,price,bought_at) VALUES(?,?,?,?,?)",(uid,category,name,price,int(time.time())))
    db.set_appearance(uid,**{slot:name}); return reply("✅ Куплено и надето: "+name,[["👤 Персонаж"],["🧥 Одежда"]])
def buy_weapon(db,vk_id,name):
    found=next((x for x in WEAPONS if x[0]==name),None)
    if not found:return reply("❌ Оружие отсутствует в каталоге.",[["🔫 Оружие"]])
    _,price,code=found; uid=player_id_by_vk(db,vk_id); user=db.user(uid)
    if not user or user["balance"]<price:return reply("❌ Недостаточно денег.",[["🔫 Оружие"]])
    with _conn(db) as c:c.execute("UPDATE users SET balance=balance-? WHERE id=?",(price,uid)); c.execute("INSERT INTO v5_weapons(user_id,code,name,price,bought_at) VALUES(?,?,?,?,?)",(uid,code,found[0],price,int(time.time())))
    return reply("🔫 Куплено: "+found[0],[["🔫 Оружие"],["🏙️ Главное меню"]])
def buy_premium(db,vk_id,name):
    found=next((x for x in PREMIUM if x[0]==name),None)
    if not found:return reply("❌ Премиум-товар отсутствует.",[["💎 Премиум"]])
    _,price,code=found; uid=player_id_by_vk(db,vk_id); user=db.user(uid)
    if not user or user["balance"]<price:return reply("❌ Недостаточно денег.",[["💎 Премиум"],["🏙️ Главное меню"]])
    with _conn(db) as c:c.execute("UPDATE users SET balance=balance-? WHERE id=?",(price,uid)); c.execute("INSERT INTO v5_purchases(user_id,code,name,price,bought_at) VALUES(?,?,?,?,?)",(uid,code,found[0],price,int(time.time())))
    return reply("💎 Активировано: "+found[0],[["💎 Премиум"],["🏙️ Главное меню"]])
