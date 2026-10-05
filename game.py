import random
import time


def money(n):
    return f"${int(n):,}".replace(",", " ")


class Game:
    JOBS = {
        "taxi": ("🚕 Таксист", 15000, 10),
        "federal": ("🕵️ Федерал", 30000, 15),
        "block": ("📦 Блок", 22000, 12),
        "refwork": ("🔗 Рефка", 40000, 20),
    }
    CARS = {
        "common": [
            ("Clover",10,1_000_000), ("Elegy",12,2_000_000),
            ("Falcon Compact",52,18_000), ("Vektor Sedan",64,35_000),
        ],
        "sport": [
            ("Sultan",20,8_000_000), ("Banshee",25,12_000_000),
            ("Raptor Coupe",79,65_000), ("Night Runner",91,145_000),
        ],
        "super": [
            ("Infernus",40,50_000_000), ("Turismo",45,65_000_000),
            ("Bullet GT",97,250_000), ("Phantom X",99,450_000),
        ],
        "lowrider": [
            ("Savanna",14,5_000_000), ("Voodoo",16,6_000_000),
        ],
        "special": [
            ("Titan SUV",68,90_000), ("Iron Wolf",88,180_000),
        ],
    }

    def __init__(self, db, admins):
        self.db = db
        self.admins = admins

    NPCS = {
        "dealer": ("💰 Дилер", "Сделки и быстрые деньги."),
        "fixer": ("🕴️ Фиксер", "Заказы, связи и рискованные поручения."),
        "mechanic": ("🔧 Механик", "Машины, ремонт и уличные задания."),
        "informant": ("🕵️ Информатор", "Слухи о городе и особые задания."),
    }

    def phone(self,uid):
        rows=self.db.phone_contacts(uid)
        if not rows:
            return "📱 ТЕЛЕФОН\n\nКонтактов пока нет.\nДобавляй игроков через VK ID."
        return "📱 ТЕЛЕФОН\n\n" + "\n".join(
            f"👤 {r['nickname']} • VK {r['contact_id']}" for r in rows
        )

    def phone_add(self,uid,target):
        target=int(target)
        u=self.db.user(target)
        if not u: return "❌ Игрок не найден."
        return self.db.phone_add(uid,target,u["nickname"])[1]

    def phone_remove(self,uid,target):
        return "🗑️ Контакт удалён." if self.db.phone_remove(uid,int(target)) else "❌ Контакт не найден."

    def npc_menu(self,uid):
        return "📱 NPC ГОРОДА\n\n" + "\n".join(
            f"{title}\n{desc}\nНажми на NPC, чтобы открыть его действия."
            for title,desc in self.NPCS.values()
        )

    def npc(self,uid,code):
        if code not in self.NPCS: return "❌ NPC не найден."
        title,desc=self.NPCS[code]
        progress=self.db.npc_value(uid,code)
        return f"{title}\n\n{desc}\n\n⭐ Репутация: {progress}\n\n🎯 Доступные действия появятся по мере развития NPC."
    
    def welcome(self, uid, referral_bonus=None):
        bonus_line = ""
        if referral_bonus:
            bonus_line = "\n🤝 Реферальный бонус активирован: +$50 000\n"
        return (
            "🏙️ BANDIT CITY\n\n"
            "Добро пожаловать в город, где всё начинается с нуля.\n"
            "Зарабатывай, покупай бизнес, собирай машины и постепенно строй свою империю.\n\n"
            "💰 Стартовый капитал: $100 000\n"
            "⭐ Уровень: 1\n"
            "📍 Город: Los Santos\n"
            f"{bonus_line}\n"
            "🎓 БЫСТРЫЙ СТАРТ\n"
            "1️⃣ 💼 Найди работу и заработай первые деньги.\n"
            "2️⃣ 🏢 Купи бизнес и получай доход автоматически.\n"
            "3️⃣ 🚗 Купи машину и развивайся дальше.\n\n"
            "🎁 За приглашение друзей ты тоже получаешь бонусы.\n\n"
            "👇 Выбирай, с чего начать!"
        )

    def profile(self, uid):
        u=self.db.user(uid)
        cars=len(self.db.cars(uid))
        items=len(self.db.items(uid))
        return (
            "👤 ПРОФИЛЬ\n\n"
            f"🎭 Ник: {u['nickname']}\n🏙 {u['city']}\n"
            f"💵 Наличные: {money(u['balance'])}\n🏦 Банк: {money(u['bank'])}\n"
            f"⭐ Уровень: {u['level']}\n✨ XP: {u['xp']}\n"
            f"👥 Рефералов: {u['referrals']}\n🚗 Машин: {cars}\n🎒 Вещей: {items}\n"
            f"🔗 Код: {u['ref_code']}"
        )

    def work(self, uid, job):
        if job not in self.JOBS: return "❌ Работа не найдена."
        name,reward,xp=self.JOBS[job]
        now=int(time.time())
        last=self.db.job_last(uid,job)
        if now-last<60:
            return f"⏳ Подожди {60-(now-last)} сек."
        self.db.add_money(uid,reward)
        self.db.xp(uid,xp)
        self.db.job_set(uid,job)
        return f"✅ {name}\n💵 +{money(reward)}\n✨ +{xp} XP"

    def business_info(self,uid):
        b=self.db.business(uid)
        if not b:
            return "🏢 БИЗНЕС\n\n🏭 Аэропорт — $100 000 000\n💰 Чистыми — $40 000/мин\n📦 Сырьё — $40 000/ед."
        status="🟢 Работает" if b["stock"] else "🔴 Нет сырья"
        return (
            "🏢 КОНТРАБАНДИСТСКИЙ АЭРОПОРТ\n\n"
            f"{status}\n💵 Касса: {money(b['balance'])}\n"
            f"📦 Склад: {b['stock']:,}/5 000 000\n"
            f"💰 Валовый доход: $80 000/мин\n"
            "📈 Чистая прибыль: $40 000/мин\n"
            "📦 1 минута = 1 единица сырья"
        ).replace(",", " ")

    def buy_business(self,uid):
        return self.db.buy_business(uid)

    def refill_stock(self,uid,amount):
        return self.db.refill(uid,amount)

    def withdraw_business(self,uid):
        return self.db.withdraw(uid)

    def apply_referral(self,uid,code):
        if self.db.referral(uid,code):
            return "🎁 Реферал активирован! Ты получил $50 000."
        return None

    def ref_link(self,uid):
        u=self.db.user(uid)
        return f"🔗 ТВОЙ КОД: {u['ref_code']}\n/start {u['ref_code']}\n\n🎁 Ты получаешь $100 000 за нового игрока."

    def bank(self,uid,action,amount):
        if action == "deposit":
            return self.db.bank_deposit(uid, amount)
        return self.db.bank_withdraw(uid, amount)

    def daily(self,uid):
        return self.db.daily(uid)

    def achievements(self,uid):
        return self.db.achievements(uid)

    def transfer(self,uid,target,amount):
        return self.db.transfer(uid,target,amount)

    def attack(self,uid,target,mode):
        return self.db.attack(uid,target,mode)

    def catalog(self,cat):
        title={"common":"🚙 ОБЫЧНЫЕ","sport":"🏎 СПОРТ","super":"🔥 СУПЕРКАРЫ","lowrider":"💿 ЛОУРАЙДЕРЫ","special":"🚘 СПЕЦТРАНСПОРТ"}[cat]
        out=[title,""]
        for model,speed,price in self.CARS[cat]:
            out.append(f"🚗 {model}\n⚡ {speed} км/мин\n💵 {money(price)}\n/buycar {model}\n")
        return "\n".join(out)

    def buy_car(self,uid,model):
        return self.db.buy_car(uid,model)

    def sell_car(self,uid,cid):
        return self.db.sell_car(uid,cid)

    def garage(self,uid):
        rows=self.db.cars(uid)
        if not rows: return "🚘 Гараж пуст."
        return "🚘 ГАРАЖ\n\n"+"\n".join(
            f"ID {r['id']} | {r['model']} | ⚡{r['speed']} | {money(r['price'])}\n/sellcar {r['id']} — 70%"
            for r in rows
        )

    def buy_item(self,uid,name,price):
        return self.db.buy_item(uid,name,price)

    def sell_item(self,uid,iid):
        return self.db.sell_item(uid,iid)

    def items(self,uid):
        rows=self.db.items(uid)
        if not rows: return "🎒 Вещей нет."
        return "🎒 ВЕЩИ\n\n"+"\n".join(
            f"ID {r['id']} | {r['name']} | {money(r['price'])}\n/sellitem {r['id']} — 70%"
            for r in rows
        )

    def casino(self,uid,cmd):
        bet=10_000
        u=self.db.user(uid)
        if u["balance"]<bet: return "❌ Нужно $10 000."
        self.db.add_money(uid,-bet)
        if cmd=="🎲 Кости":
            a,b=random.randint(1,6),random.randint(1,6)
            if a+b>=8:
                self.db.add_money(uid,bet*2)
                return f"🎲 {a}+{b}={a+b}\n🎉 +{money(bet*2)}"
            return f"🎲 {a}+{b}={a+b}\n❌ -{money(bet)}"
        if cmd=="🎰 Слоты":
            s=[random.choice(["🍒","🍋","💎","7️⃣"]) for _ in range(3)]
            if len(set(s))==1:
                self.db.add_money(uid,bet*5); return f"🎰 {' | '.join(s)}\n🎉 ДЖЕКПОТ +{money(bet*5)}"
            if len(set(s))==2:
                self.db.add_money(uid,bet*2); return f"🎰 {' | '.join(s)}\n✨ +{money(bet*2)}"
            return f"🎰 {' | '.join(s)}\n❌ -{money(bet)}"
        if cmd=="🎯 Рулетка":
            n=random.randint(0,36)
            if n and n%2==0:
                self.db.add_money(uid,bet*2); return f"🎯 {n}\n🎉 +{money(bet*2)}"
            return f"🎯 {n}\n❌ -{money(bet)}"
        p,d=random.randint(16,21),random.randint(17,21)
        if p>d:
            self.db.add_money(uid,bet*2); return f"🃏 Ты {p} | Дилер {d}\n🎉 +{money(bet*2)}"
        if p==d:
            self.db.add_money(uid,bet); return f"🃏 Ты {p} | Дилер {d}\n🤝 Ничья"
        return f"🃏 Ты {p} | Дилер {d}\n❌ -{money(bet)}"

    def top(self):
        return self.db.top()

    def admin_command(self,uid,text):
        p=text.split()
        if len(p)==1: return (
            "👑 АДМИН-ПАНЕЛЬ\n\n"
            "/admin stats\n/admin top\n"
            "/admin give VK_ID SUM\n/admin take VK_ID SUM\n"
            "/admin level VK_ID LEVEL\n/admin stock VK_ID AMOUNT\n"
            "/admin ban VK_ID\n/admin unban VK_ID"
        )
        if p[1]=="stats": return self.db.admin_stats()
        if p[1]=="top": return self.db.top()
        try:
            target=int(p[2])
            if p[1] in ("give","take"):
                amount=int(p[3])
                if amount <= 0:
                    return "❌ Сумма должна быть положительной."
                ok=self.db.admin_money(target, amount if p[1]=="give" else -amount)
                return "✅ Баланс изменён." if ok else "❌ Игрок не найден."
            if p[1]=="level":
                ok=self.db.admin_level(target,int(p[3]))
                return "✅ Уровень изменён." if ok else "❌ Игрок не найден."
            if p[1]=="stock":
                return "✅ Склад изменён." if self.db.admin_stock(target,int(p[3])) else "❌ Нет игрока или бизнеса."
            if p[1]=="ban":
                return "⛔ Игрок заблокирован." if self.db.admin_ban(target,True) else "❌ Игрок не найден."
            if p[1]=="unban":
                return "✅ Игрок разблокирован." if self.db.admin_ban(target,False) else "❌ Игрок не найден."
        except (ValueError,IndexError):
            return "❌ Неверные параметры."
        return "❌ Неизвестная админ-команда."
