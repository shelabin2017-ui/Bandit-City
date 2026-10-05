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
    
    SMS_TASKS = {
        "first_job": ("💼 Первое дело", "Найди работу и выполни первую смену.", 25000, 20),
        "first_car": ("🚗 Первая машина", "Купи свою первую машину.", 50000, 30),
        "first_business": ("🏢 Свой бизнес", "Купи первый бизнес.", 100000, 50),
    }

    STORY = [
        ("ГЛАВА 1 • НОВИЧОК", "Ты приехал в Los Santos с пустыми карманами. Город никого не ждёт — его нужно брать самому."),
        ("ГЛАВА 2 • ПЕРВЫЕ СВЯЗИ", "Работа приносит деньги, но настоящие возможности появляются через людей. Телефон становится твоим главным инструментом."),
        ("ГЛАВА 3 • ТЕНЬ ГОРОДА", "Ты начинаешь замечать, что за обычными заказами скрывается большая игра. Кто-то следит за твоими шагами."),
    ]

    TUTORIAL = [
        ("👋 Добро пожаловать", "Это Bandit City. Здесь ты начинаешь с нуля и сам строишь свою историю."),
        ("💼 Работа", "Открой «Работа», выбери профессию и выполни первую смену."),
        ("🏦 Деньги", "Часть денег держи в банке, а наличные используй для покупок и действий."),
        ("🚗 Машины", "Открой «Авто», выбери машину и постепенно собирай свой гараж."),
        ("📱 Телефон", "Через телефон можно хранить контакты и общаться с NPC."),
        ("🎰 Казино", "Казино — рискованный способ заработать. Следи за балансом и ставками."),
        ("🎯 Миссии", "Выполняй миссии, чтобы получать дополнительные деньги и XP."),
        ("🏆 Ачивки", "Ачивки фиксируют важные достижения и показывают прогресс."),
    ]

    def sms(self,uid):
        rows=self.db.sms_list(uid)
        tasks=self.db.sms_task_rows(uid,list(self.SMS_TASKS))
        if not rows:
            body="📩 СМС\n\nПока сообщений нет."
        else:
            body="📩 СМС\n\n" + "\n\n".join(
                f"{'🔵' if not r['read'] else '⚪'} {r['sender']}\n{r['text']}"
                for r in rows
            )
        task_lines=["\n🎯 ЗАДАНИЯ ИЗ СМС"]
        for code,(title,desc,cash,xp) in self.SMS_TASKS.items():
            r=tasks.get(code)
            if r and r["claimed"]:
                status="✅ Получено"
            elif r and r["completed"]:
                status="🎁 ГОТОВО"
            else:
                status="⏳ Не выполнено"
            task_lines.append(f"{title} — {status}\n{desc}\n🎁 {money(cash)} + {xp} XP")
        return body+"\n"+"\n".join(task_lines)

    def complete_sms_task(self,uid,code):
        if code not in self.SMS_TASKS:
            return "❌ СМС-задание не найдено."
        title,desc,cash,xp=self.SMS_TASKS[code]
        return self.db.sms_task_claim(uid,code,cash,xp)[1]

    def tutorial(self,uid):
        r=self.db.tutorial(uid)
        step=min(int(r["step"]),len(self.TUTORIAL)-1)
        title,text=self.TUTORIAL[step]
        if r["completed"]:
            return "🎓 ОБУЧЕНИЕ\n\n✅ Обучение завершено. Ты готов к городу."
        return f"🎓 ОБУЧЕНИЕ\n\n{step+1}/{len(self.TUTORIAL)}\n{title}\n\n{text}"

    def tutorial_next(self,uid):
        r=self.db.tutorial(uid)
        step=int(r["step"])+1
        if step>=len(self.TUTORIAL):
            self.db.tutorial_set(uid,len(self.TUTORIAL),True)
            self.db.complete_onboarding(uid)
            return "🎓 ОБУЧЕНИЕ ЗАВЕРШЕНО\n\n🏙️ Город открыт. Удачи."
        self.db.tutorial_set(uid,step,False)
        title,text=self.TUTORIAL[step]
        return f"🎓 ОБУЧЕНИЕ\n\n{step+1}/{len(self.TUTORIAL)}\n{title}\n\n{text}"

    def story(self,uid):
        r=self.db.story(uid)
        chapter=max(1,min(int(r["chapter"]),len(self.STORY)))
        title,text=self.STORY[chapter-1]
        return f"📖 СЮЖЕТ\n\n{title}\n\n{text}\n\n📍 Глава {chapter}/{len(self.STORY)}"

    def achievements_full(self,uid):
        base=self.db.achievements(uid)
        return "🏆 АЧИВКИ\n\n"+str(base)

    MISSIONS = {
        "work_3": ("💼 Рабочая смена", 3, "Выполни 3 рабочие смены.", 75000, 40),
        "earn_100k": ("💵 Заработок", 100000, "Заработай $100 000 на работе.", 100000, 60),
        "casino_3": ("🎰 Азарт", 3, "Сыграй 3 раза в казино.", 50000, 35),
        "casino_win": ("🍀 Удача", 1, "Выиграй игру в казино.", 80000, 50),
        "rich": ("💰 Капитал", 1, "Накопи $1 000 000.", 150000, 80),
        "ref_1": ("🤝 Связи", 1, "Пригласи игрока.", 100000, 70),
    }

    def missions(self,uid):
        rows=self.db.mission_rows(uid,list(self.MISSIONS))
        out=["🎯 МИССИИ",""]
        for code,(title,target,desc,cash,xp) in self.MISSIONS.items():
            r=rows.get(code)
            progress=int(r["progress"]) if r else 0
            claimed=bool(r["claimed"]) if r else False
            status="✅ Получено" if claimed else ("🎁 ГОТОВО" if progress>=target else f"{progress}/{target}")
            out.append(f"{title} — {status}\n{desc}\n🎁 {money(cash)} + {xp} XP")
        return "\n\n".join(out)

    def claim_mission(self,uid,code):
        if code not in self.MISSIONS:
            return "❌ Миссия не найдена."
        _,target,_,cash,xp=self.MISSIONS[code]
        return self.db.mission_claim(uid,code,cash,xp,target)[1]

    def casino_info(self,uid):
        r=self.db.casino_stats(uid)
        if not r:
            return "🎰 СТАТИСТИКА КАЗИНО\n\nИгр: 0\nПобед: 0\nПоражений: 0\nОборот: $0\nРезультат: $0"
        return (f"🎰 СТАТИСТИКА КАЗИНО\n\n🎮 Игр: {r['plays']}\n"
                f"🏆 Побед: {r['wins']}\n❌ Поражений: {r['losses']}\n"
                f"💰 Оборот: {money(r['wagered'])}\n📈 Результат: {money(r['profit'])}")

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
        if not self.db.sms_task_rows(uid,["first_job"]).get("first_job",{}).get("completed",0):
            self.db.sms_task_complete(uid,"first_job")
            self.db.sms_add(uid,"📱 Неизвестный номер","Первое дело сделано. Теперь город знает, что ты умеешь работать.","first_job",25000,20)
        self.db.mission_add(uid,"work_3",1)
        self.db.mission_add(uid,"earn_100k",reward)
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
        result=self.db.buy_business(uid)
        if "успеш" in result.lower() or "куплен" in result.lower():
            if not self.db.sms_task_rows(uid,["first_business"]).get("first_business",{}).get("completed",0):
                self.db.sms_task_complete(uid,"first_business")
                self.db.sms_add(uid,"🕴️ Фиксер","Теперь у тебя есть своё дело. Деньги любят тех, кто умеет ими управлять.","first_business",100000,50)
        return result

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
        result=self.db.buy_car(uid,model)
        if "успеш" in result.lower() or "куплен" in result.lower():
            if not self.db.sms_task_rows(uid,["first_car"]).get("first_car",{}).get("completed",0):
                self.db.sms_task_complete(uid,"first_car")
                self.db.sms_add(uid,"🔧 Механик","Поздравляю с первой машиной. Заезжай, если понадобится ремонт.","first_car",50000,30)
        return result

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
        if u["balance"]<bet:
            return "❌ Нужно $10 000."
        self.db.add_money(uid,-bet)
        won=False
        profit=-bet
        if cmd=="🎲 Кости":
            a,b=random.randint(1,6),random.randint(1,6)
            if a+b>=8:
                payout=bet*2
                self.db.add_money(uid,payout)
                won=True
                profit=payout-bet
                result=f"🎲 {a}+{b}={a+b}\n🎉 +{money(payout)}"
            else:
                result=f"🎲 {a}+{b}={a+b}\n❌ -{money(bet)}"
        elif cmd=="🎰 Слоты":
            reels=[random.choice(["🍒","🍋","💎","7️⃣"]) for _ in range(3)]
            if len(set(reels))==1:
                payout=bet*5
                self.db.add_money(uid,payout)
                won=True
                profit=payout-bet
                result=f"🎰 {' | '.join(reels)}\n🎉 ДЖЕКПОТ +{money(payout)}"
            elif len(set(reels))==2:
                payout=bet*2
                self.db.add_money(uid,payout)
                won=True
                profit=payout-bet
                result=f"🎰 {' | '.join(reels)}\n✨ +{money(payout)}"
            else:
                result=f"🎰 {' | '.join(reels)}\n❌ -{money(bet)}"
        elif cmd=="🎯 Рулетка":
            n=random.randint(0,36)
            if n and n%2==0:
                payout=bet*2
                self.db.add_money(uid,payout)
                won=True
                profit=payout-bet
                result=f"🎯 {n}\n🎉 +{money(payout)}"
            else:
                result=f"🎯 {n}\n❌ -{money(bet)}"
        else:
            p,d=random.randint(16,21),random.randint(17,21)
            if p>d:
                payout=bet*2
                self.db.add_money(uid,payout)
                won=True
                profit=payout-bet
                result=f"🃏 Ты {p} | Дилер {d}\n🎉 +{money(payout)}"
            elif p==d:
                self.db.add_money(uid,bet)
                profit=0
                won=False
                result=f"🃏 Ты {p} | Дилер {d}\n🤝 Ничья"
            else:
                result=f"🃏 Ты {p} | Дилер {d}\n❌ -{money(bet)}"
        self.db.casino_record(uid,bet,profit,won)
        self.db.mission_add(uid,"casino_3",1)
        if won:
            self.db.mission_add(uid,"casino_win",1)
        return result

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
