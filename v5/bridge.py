"""V5 shop layer. Public catalogue is separated from event-only drops."""
import time
from catalog import EVENTS, EVENT_EXCLUSIVES, active_events

MAINTENANCE = False
ADMIN_IDS = set()

ITEMS = [
    ("💻 MacBook", 120000), ("👟 Кроссовки", 25000), ("👕 Куртка", 45000),
    ("💇 Волосы", 30000), ("📱 Burner Phone", 65000), ("🧰 Набор отмычек", 85000),
    ("🩹 Аптечка", 30000), ("⚡ Энергетик", 15000), ("🎭 Маска", 45000),
    ("🛡 Бронежилет", 180000), ("🧰 Инструменты", 95000), ("🍀 Счастливый жетон", 125000),
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

WEAPONS = [("🔪 Нож",15000,"knife"),("🔫 Пистолет",75000,"pistol"),("🔫 Desert Eagle",180000,"deagle"),("🔫 Дробовик",250000,"shotgun"),("🔫 SMG",350000,"smg")]
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
def item_shop():
    body=["🛒 ПРЕДМЕТЫ LOS SANTOS","","Постоянный каталог:",""]; buttons=[]
    item_buttons=[]
    for name,price in ITEMS:
        body += [name,"💵 "+money(price),""]
        item_buttons.append(name+" — "+money(price))
    # Reserve 3 rows for navigation; VK default keyboards support at most 10 rows.
    # The catalog itself may therefore use at most 7 rows.
    for i in range(0, len(item_buttons), 2):
        if len(buttons) >= 7:
            break
        buttons.append(item_buttons[i:i + 2])
    buttons += [["🎒 Инвентарь"],["🛒 Магазин"],["🏙️ Главное меню"]]
    return reply("\n".join(body),buttons)
def inventory(db,vk_id):
    uid=player_id_by_vk(db,vk_id); rows=db.items(uid)
    if not rows: return reply("🎒 ИНВЕНТАРЬ LOS SANTOS\n\nКарман пуст.",[["🛒 Магазин"],["🏙️ Главное меню"]])
    body=["🎒 ИНВЕНТАРЬ LOS SANTOS",""]; buttons=[]; sell_buttons=[]
    for row in rows:
        body += ["📦 "+row["name"],"💵 Цена: "+money(row["price"]),""]
        sell_buttons.append("🗑 Продать #"+str(row["id"]))
    # Reserve 3 rows for navigation; keep inventory actions within 7 rows.
    for i in range(0, len(sell_buttons), 2):
        if len(buttons) >= 7:
            break
        buttons.append(sell_buttons[i:i + 2])
    buttons += [["🛒 Магазин"],["🏙️ Главное меню"]]
    return reply("\n".join(body),buttons)
def clothing_menu():
    return reply("🧥 ОДЕЖДА LOS SANTOS\n\nПостоянные категории. Эксклюзивы выдаются отдельно.",[["🧢 Головные уборы","👕 Верх"],["👖 Брюки","🥾 Обувь"],["💍 Аксессуары","💇 Волосы"],["↩️ В магазин"],["👤 Персонаж","🏙️ Главное меню"]])
def event_catalog():
    active=active_events()
    body=["🎪 ИВЕНТ-ДРОПЫ","","🔒 Не продаются за обычные деньги.","Выдаются событиями или секретными промокодами.",""]
    buttons=[]
    for key,event in EVENTS.items():
        is_active=key in active
        state="🟢 АКТИВЕН" if is_active else "⚪ ЗАКРЫТ"
        body += [f"📅 {event['title']} • {state}",event['description'],f"🎁 {len(event['drops'])} эксклюзивов",""]
        if is_active: buttons.append([f"🎪 {event['title']}"])
    if not buttons: body.append("⏳ Сейчас активных ивентов нет.")
    buttons += [["↩️ В магазин"],["🏙️ Главное меню"]]
    return reply("\n".join(body),buttons)
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
