import random
import time

from catalog import EVENTS


def money(n):
    return f"${int(n):,}".replace(",", " ")


class Game:
    # Профессии дают разные выплаты и XP; общий лимит на действие проверяется
    # текущей таблицей jobs, поэтому каждая профессия имеет отдельный cooldown.
    JOBS = {
        "taxi": ("🚕 Таксист", 15000, 10),
        "federal": ("🕵️ Федерал", 30000, 15),
        "block": ("📦 Блок", 22000, 12),
        "refwork": ("🔗 Рефка", 40000, 20),
        "courier": ("🛵 Курьер", 9000, 8),
        "builder": ("👷 Строитель", 18000, 11),
        "mechanic": ("🔧 Автомеханик", 24000, 14),
        "medic": ("🚑 Медик", 26000, 16),
        "cook": ("👨‍🍳 Повар", 12000, 9),
        "miner": ("⛏ Шахтёр", 28000, 15),
        "security": ("🛡 Охранник", 21000, 13),
        "programmer": ("💻 Разработчик", 35000, 18),
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

    def record_event_action(self,uid,action,amount=1):
        """Count actions only while a matching time-limited event is active."""
        from catalog import active_events
        from event_announcer import active_events as runtime_active_events
        for event in runtime_active_events(self.db).values():
            if event.get("goal_action") == action and event.get("goal_code"):
                self.db.mission_add(uid,event["goal_code"],amount)

    def phone(self,uid):
        rows=self.db.phone_contacts(uid)
        if not rows:
            return "📱 ТЕЛЕФОН • ЛИНИЯ СВЯЗИ\n\nПока в контактах пусто. Los Santos не любит одиночек — добавь знакомых игроков по VK ID, и нужный человек будет под рукой."
        return "📱 ТЕЛЕФОН\n\n" + "\n".join(
            f"👤 {r['nickname']} • VK {r['contact_id']}" for r in rows
        )

    def phone_add(self,user_id,target_vk):
        target = self.db.user_by_vk(int(target_vk))
        if not target:
            return "❌ Игрок с таким VK ID не найден."
        if int(target["id"]) == int(user_id):
            return "❌ Нельзя добавить самого себя."
        return self.db.phone_add(int(user_id), int(target["vk_id"]), target["nickname"])[1]

    def phone_remove(self,user_id,target_vk):
        return "🗑️ Контакт удалён." if self.db.phone_remove(int(user_id), int(target_vk)) else "❌ Контакт не найден."

    def npc_menu(self,uid):
        return "📱 NPC ГОРОДА\n\n" + "\n".join(
            f"{title}\n{desc}\nНажми на NPC, чтобы открыть его действия."
            for title,desc in self.NPCS.values()
        )

    def npc(self,uid,code):
        if code not in self.NPCS:
            return "❌ NPC не найден."
        title,desc=self.NPCS[code]
        progress=self.db.npc_value(uid,code)
        actions = {
            "dealer": "💰 Сделка дилера • ставка $20 000 • перерыв 10 мин.",
            "fixer": "📜 Заказ фиксера • вход $10 000 • перерыв 15 мин.",
            "mechanic": "🔧 Тюнинг авто • $75 000 за +5 скорости • перерыв 60 мин.",
            "informant": "🕵️ Слух информатора • $5 000, снижение розыска • перерыв 5 мин.",
        }
        return f"{title}\n\n{desc}\n\n⭐ Репутация: {progress}\n\n🎯 Действие: {actions[code]}"

    def npc_action(self,uid,code):
        actions = {
            "dealer": ("deal", 600),
            "fixer": ("contract", 900),
            "mechanic": ("tune", 3600),
            "informant": ("tip", 300),
        }
        if code not in actions:
            return "❌ Действие NPC не найдено."
        action, cooldown = actions[code]
        remaining = self.db.npc_cooldown_remaining(uid, code, action)
        if remaining:
            minutes, seconds = divmod(remaining, 60)
            return f"⏳ Пока рано возвращаться. Контакт ещё занят делами.\n\n🕒 Попробуй снова через {minutes} мин. {seconds} сек.\n💬 В Los Santos даже у полезных людей есть свои дела."

        user = self.db.user(uid)
        if code == "dealer":
            stake = 20_000
            if int(user["balance"]) < stake:
                return "❌ Для сделки дилера нужно $20 000 наличными."
            self.db.add_money(uid, -stake)
            self.db.status_change(uid, heat=3)
            self.db.npc_set_cooldown(uid, code, action, cooldown)
            if random.random() < 0.5:
                payout = 40_000
                self.db.add_money(uid, payout)
                self.db.npc_set(uid, code, self.db.npc_value(uid, code) + 1)
                return f"🤝 ДИЛЕР УЛЫБАЕТСЯ: СДЕЛКА ЗАШЛА\n\n💵 На руках: +{money(payout)}\n📈 Чистыми: +{money(payout-stake)}\n\n🕶️ «Сегодня тебе повезло. Не путай удачу с привычкой», — бросает дилер."
            return f"🚨 ДИЛЕР СЖИМАЕТ ПЛЕЧА: СДЕЛКА СОРВАЛАСЬ\n\n💸 Потеряно: {money(stake)}\n🚨 Розыск вырос на 3.\n\n🕶️ «Бывает. Главное — не пытайся отыграться на эмоциях»."

        if code == "fixer":
            fee = 10_000
            if int(user["balance"]) < fee:
                return "❌ Для заказа фиксера нужно $10 000 наличными."
            self.db.add_money(uid, -fee)
            self.db.npc_set_cooldown(uid, code, action, cooldown)
            if random.random() < 0.5:
                payout = 30_000
                self.db.add_money(uid, payout)
                self.db.status_change(uid, reputation=2)
                self.db.npc_set(uid, code, self.db.npc_value(uid, code) + 1)
                return f"📜 ФИКСЕР ДОВОЛЕН: ЗАКАЗ ЗАКРЫТ\n\n💵 Награда: {money(payout)}\n📈 Чистыми: +{money(payout-fee)}\n⭐ Репутация выросла.\n\n🕴️ «Работаешь тихо — и двери начинают открываться»."
            self.db.status_change(uid, heat=5)
            return f"❌ ФИКСЕР НЕ ВПЕЧАТЛЁН: ЗАКАЗ СОРВАН\n\n💸 Потерян аванс: {money(fee)}\n🚨 Розыск вырос на 5.\n\n🕴️ «В следующий раз сначала подумай, потом соглашайся»."

        if code == "mechanic":
            ok, message = self.db.tune_car(uid)
            if not ok:
                return message
            self.db.npc_set_cooldown(uid, code, action, cooldown)
            self.db.npc_set(uid, code, self.db.npc_value(uid, code) + 1)
            return message

        fee = 5_000
        if int(user["balance"]) < fee:
            return "❌ Информатору нужно $5 000 наличными."
        self.db.add_money(uid, -fee)
        self.db.status_change(uid, heat=-15, reputation=1)
        self.db.npc_set_cooldown(uid, code, action, cooldown)
        self.db.city_event_seed()
        events = self.db.city_event_list()
        rumor = events[0]["title"] if events else "По улицам ходят слухи, но пока никто не готов говорить вслух."
        self.db.npc_set(uid, code, self.db.npc_value(uid, code) + 1)
        return f"🕵️ СЛУХИ ИНФОРМАТОРА\n\n🗞️ {rumor}\n\n🚨 Розыск снижен на 15.\n💵 Оплата: {money(fee)}\n⭐ Репутация выросла."
    
    SMS_TASKS = {
        "first_job": ("💼 Первое дело", "Найди работу и выполни первую смену.", 25000, 20),
        "first_car": ("🚗 Первая машина", "Купи свою первую машину.", 50000, 30),
        "first_business": ("🏢 Свой бизнес", "Купи первый бизнес.", 100000, 50),
    }

    STORY = [
        ("ГЛАВА 1 • НОВИЧОК", "Автобус шипит дверями и уходит в ночь. Ты остаёшься под неоном Los Santos — с мелочью в кармане и незнакомым номером в телефоне. Сообщение приходит почти сразу: «Добро пожаловать. Не обольщайся — город никому ничего не должен. Хочешь остаться? Найди работу и покажи, что умеешь держать слово». У закусочной парень в кожаной куртке замечает тебя и кивает на экран: «Первое дело простое. Открой «💼 Работа» и закончи смену. Посмотрим, из какого ты теста»."),
        ("ГЛАВА 2 • ПЕРВЫЕ СВЯЗИ", "Смена выжала из тебя силы, но в кармане уже звенят первые деньги. Парень в кожаной куртке поднимает стакан: «Ну вот. Вчера ты был никем, сегодня хотя бы не зря потратил день». Телефон вибрирует — новое сообщение от человека, которого ты пока не знаешь. «Открой «📩 СМС». В этом городе иногда одно сообщение стоит больше, чем полный кошелёк»."),
        ("ГЛАВА 3 • ТЕНЬ ГОРОДА", "Тёмная машина снова стоит на том же перекрёстке. Заказчик, вчера считавший каждую купюру, вдруг предлагает подозрительно щедрые деньги. В СМС появляется имя, которое ты уже видел возле чужого подъезда. Проводник больше не улыбается: «Запомни, новичок: в Los Santos случайности обычно кому-то выгодны. Если тобой заинтересовались — выясни кто и зачем. Только не лезь туда, откуда не сможешь выйти». Следи за сообщениями, выполняй дела и укрепляй своё положение. Теперь ты уже не просто прохожий."),
    ]

    # Пошаговая экскурсия по всем разделам. Индексы используются bot.py
    # для показа соответствующих реальных названий кнопок VK.
    TUTORIAL = [
        ("📖 СЮЖЕТНЫЙ ПРОЛОГ • Ночной город", "Автобус уходит, оставляя тебя один на один с неоном Los Santos. В телефоне вспыхивает сообщение с неизвестного номера: «Хочешь здесь остаться — сначала докажи, что можешь заработать». Из тени выходит парень в кожаной куртке: «Я покажу тебе город. Но запомни: подсказки не вечны, дальше придётся решать самому». Это не отдельная лекция, а твоя первая глава в городе. Пройдёшь её один раз — и вступление больше не вернётся."),
        ("💼 Этап 1/12 • Первая работа", "Телефон оживает: «Хватит стоять на остановке. Найди работу — в этом городе уважение начинается с дела». Открой «💼 Работа», выбери профессию и выполни первую смену. Получишь первые деньги и опыт, а заодно докажешь, что на тебя можно положиться."),
        ("💵 Этап 2/12 • Деньги, профиль и статус", "Проводник кивает на экран телефона: «Здесь твоя визитка». В «👤 Профиль» найдёшь ник, уровень, деньги, банк, машины и личный код. А «📊 Мой статус» покажет, сколько осталось энергии, насколько ты голоден и в каком состоянии персонаж. Не игнорируй эти показатели — город быстро напоминает о себе тем, кто забывает поесть и отдохнуть."),
        ("💼 Этап 3/12 • Работа и бизнес", "Твой новый знакомый кивает на оживлённую улицу: «Работа кормит сегодня, бизнес может кормить завтра». В «💼 Работа» выбирай профессию и выходи на смены, а в «🏢 Бизнес» следи за кассой и доходом. Накопишь капитал — сможешь открыть собственное дело."),
        ("🚗 Этап 4/12 • Авто и магазин", "Мимо с рёвом пролетает купе. Проводник усмехается: «Когда-нибудь и у тебя будут ключи от своей тачки». В «🚗 Авто» ищи машины и развивай автопарк. В «🛒 Магазин» покупай полезные предметы — только сначала смотри цену и назначение. Красивые вещи радуют, но пустой кошелёк не прощает импульсивных покупок."),
        ("🏦 Этап 5/12 • Банк и казино", "В «🏦 Банк» храни часть капитала отдельно от наличных. Из соседнего здания доносится звон фишек. «В казино можно сорвать куш, а можно выйти с пустыми руками», — предупреждает знакомый. Если решишь испытать удачу, помни: ставка может сгореть. Не рискуй деньгами, которые откладываешь на важную покупку."),
        ("👥 Этап 6/12 • Игроки и телефон", "«👥 Игроки» помогает взаимодействовать с другими участниками города. «📱 Телефон» — контакты и городские NPC; проверяй доступные действия и сообщения."),
        ("🎯 Этап 7/12 • Миссии и события", "«🎯 Миссии» дают цели и дополнительные награды. «🌆 События города» показывают временные активности и прогресс участия. Следи за условиями события, чтобы не пропустить награду."),
        ("🎒 Этап 8/12 • Инвентарь, потребности и СМС", "Проводник стучит пальцем по экрану: «Всё, что добыл, ищи в “🎒 Инвентарь”. За состоянием следи в “🍔 Потребности” — голод и энергия могут помешать делу. А “📩 СМС” не оставляй без внимания: там бывают заказы, подсказки и задания с наградой. Иногда одно сообщение стоит дороже, чем кажется»."),
        ("🏆 Этап 9/12 • Рейтинг, достижения и бонусы", "«🏆 Рейтинг» сравнивает результаты игроков. «🏆 Достижения» фиксируют важные успехи. «🎁 Бонус» позволяет забрать доступную ежедневную награду."),
        ("📚 Этап 10/12 • Дополнительные разделы", "Нажми «📚 Ещё»: там находятся сюжет, промокод, настройки и помощь. Твой проводник хлопает тебя по плечу: «Экскурсия закончится — город никуда не денется. Дальше сам выбираешь, кем стать». После пролога вступительные подсказки больше не повторяются. Новые главы и повороты истории будут ждать в «📖 Сюжет»."),
        ("📖 Этап 11/12 • Сюжет, настройки и помощь", "«📖 Сюжет» раскрывает историю города. «⚙️ Настройки» — параметры профиля. «🎟 Промокод» — ввод действующего кода. «❓ Помощь» объясняет основные возможности и способы управления."),
        ("👑 Этап 12/12 • Об авторе проекта", "В «👑 О создателе» можно прочитать информацию об авторе Bandit City. Этот раздел находится в меню «📚 Ещё». Поддержка проекта и обратная связь помогают развивать город."),
        ("🏁 ПРОЛОГ ЗАВЕРШЁН", "🏁 Ну что, теперь ты уже не турист с автобусной остановки — ты часть Los Santos. Пролог сохранён и больше не появится. Твой проводник кивает на прощание: «Дальше сам. Зарабатывай, заводи связи, собирай тачки и строй своё дело. И запомни: в этом городе каждый что-то скрывает». Вступление закончено, но настоящая история только начинается. Следующая глава ждёт в «📖 Сюжет»."),
    ]

    TUTORIAL_VIEWS = {
        "👤 Профиль": "Твой паспорт в Los Santos 😎 Здесь ник, уровень, наличные, банк, машины, предметы и реферальный код. Заглядывай сюда, чтобы быстро проверить, как идут дела.",
        "📊 Мой статус": "Проверка состояния 🩺 Энергия и голод влияют на некоторые действия. Если показатели просели, загляни в «🍔 Потребности» и приведи себя в порядок.",
        "💼 Работа": "Время превращать планы в наличные 💸 Выбери профессию и нажми на неё, чтобы выйти на смену. Получишь деньги и опыт, но потратишь энергию. Если вымотался или сильно проголодался — сначала восстановись, потом снова в дело.",
        "🏢 Бизнес": "Работа приносит деньги за смену, а бизнес может зарабатывать, пока ты занят другим 🏢 Перед покупкой проверь цену и доход. После покупки следи за складом: без сырья производство встанет. Накопленную кассу нужно забирать отдельно.",
        "🚗 Авто": "Тачки — это статус и возможности 🚗 В гараже смотри свой автопарк, а в автосалоне выбирай следующую машину. Сначала оцени цену, потом жми газ.",
        "🛒 Магазин": "Здесь есть еда, напитки и вещи для выживания в городе 🛒 Открой категорию, прочитай описание и проверь цену. Кнопки x1, x5 и x10 покупают выбранное количество — перед подтверждением оцени общую сумму.",
        "🏦 Банк": "Спрячь часть заработка от лишних соблазнов 🏦 Вноси деньги в банк или снимай их, когда понадобятся наличные. Перед операцией проверь сумму.",
        "🎰 Казино": "Испытать удачу? 🎰 Можно выиграть, а можно остаться ни с чем. Ставь только те деньги, потеря которых не сломает твои планы.",
        "👥 Игроки": "Los Santos не пустой — здесь другие игроки 👥 Ищи участников и используй доступные действия для взаимодействия. Перед важной операцией проверь ник и сумму.",
        "📱 Телефон": "Телефон — контакты и NPC, а также доступные городские взаимодействия.",
        "🎯 Миссии": "Миссии — цели с условиями и наградами. Проверяй прогресс и забирай доступные награды.",
        "🌆 События города": "События города — временные активности. Смотри условия, срок и прогресс.",
        "🎒 Инвентарь": "Всё добытое — здесь 🎒 У предметов будут понятные действия: еду и напитки можно использовать, подарочный бокс — открыть, ненужную вещь — продать. Нажимай кнопку действия под предметом; вводить внутренние номера вручную не нужно.",
        "🍔 Потребности": "Потребности — показатели состояния персонажа; при низкой энергии или сильном голоде некоторые действия недоступны.",
        "📩 СМС": "Не оставляй телефон без внимания 📩 Тут могут появиться заказы, сюжетные повороты, подсказки и задания с наградами. Иногда одно сообщение меняет весь расклад.",
        "🏆 Рейтинг": "Рейтинг — сравнение игровых результатов и положения среди участников.",
        "🏆 Достижения": "Достижения — список открытых успехов и целей прогресса.",
        "🎁 Бонус": "Бонус — ежедневная награда, когда она доступна.",
        "📚 Ещё": "В «Ещё» собраны дополнительные разделы, которые не помещаются в главное меню.",
        "📖 Сюжет": "Сюжет — история Bandit City, главы и контекст происходящего в городе.",
        "🎟 Промокод": "Промокод — активация действующего кода, если он у тебя есть.",
        "⚙️ Настройки": "Настройки — параметры игрового профиля.",
        "❓ Помощь": "Запутался? Ничего страшного 💬 Открой помощь, чтобы разобраться с разделами и понять, что делать дальше.",
        "👑 О создателе": "«О создателе» рассказывает об авторе проекта. Кнопка находится в меню «📚 Ещё».",
    }

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
            return "🏙️ LOS SANTOS • ТЫ УЖЕ СВОЙ\n\n✅ Пролог пройден и сохранён — возвращаться к нему больше не нужно. Проводник растворился в ночной толпе, оставив последнее сообщение: «Теперь город твой. Не жди приглашения — сам создавай себе имя». Открывай «📖 Сюжет»: впереди новые дела, неожиданные встречи и тайны, которые не раскрываются за один вечер."
        return f"🏙️ LOS SANTOS • ТВОЯ ИСТОРИЯ\n\n🎬 Эпизод {step+1}/{len(self.TUTORIAL)}\n{title}\n\n{text}\n\n💬 Проводник усмехается: «Не торопись. Осмотрись, попробуй действие из подсказки, а когда будешь готов — жми «➡️ Далее экскурсии».»"

    def tutorial_view(self,uid,button):
        return "🧭 ЭКСКУРСИЯ ПО МЕНЮ\n\n" + self.TUTORIAL_VIEWS.get(
            str(button), "Этот раздел не включён в краткую экскурсию. Открой «❓ Помощь» для общей справки."
        ) + "\n\nВернись к экскурсии кнопкой «↩️ К экскурсии». Прогресс обучения не изменён."

    def tutorial_next(self,uid):
        r=self.db.tutorial(uid)
        current=int(r["step"])
        if current == 1 and self.db.needs_onboarding(uid) and not self.db.sms_task_rows(uid,["first_job"]).get("first_job",{}).get("completed",0):
            return "📖 ПЕРВОЕ ДЕЛО • ГОРОД ЖДЁТ\n\n📱 Новое сообщение от проводника: «Связи сами себя не построят, а в кармане пока пусто. Открой “💼 Работа”, выбери профессию и закончи первую смену. Не переживай — я не исчезну. Вернёшься, и продолжим с того же места».\n\n💵 Первая смена принесёт деньги и опыт. Без неё следующая глава не откроется."
        step=current+1
        if step>=len(self.TUTORIAL):
            self.db.tutorial_set(uid,len(self.TUTORIAL),True)
            self.db.complete_onboarding(uid)
            return "🏁 ПРОЛОГ ЗАВЕРШЁН\n\n🏙️ Вот теперь другое дело! Ты уже не случайный пассажир — Los Santos начинает запоминать твоё имя. Вступительный путь сохранён: он больше не появится в меню и не будет отвлекать тебя.\n\n🧥 Проводник поправляет куртку и улыбается: «Дальше сам. Зарабатывай, заводи связи, собирай тачки и строй своё дело. И запомни: в этом городе каждый что-то скрывает».\n\n📖 Пролог закончен, настоящая история только начинается. Следующая глава ждёт в «📖 Сюжет»."
        self.db.tutorial_set(uid,step,False)
        title,text=self.TUTORIAL[step]
        return f"🎬 LOS SANTOS • ЭПИЗОД {step+1}/{len(self.TUTORIAL)}\n\n{title}\n\n{text}\n\n💬 Проводник уже направился дальше. Закончи этот шаг и нажми «➡️ Далее экскурсии» — посмотрим, что город приготовил следующим."

    def story(self,uid):
        r=self.db.story(uid)
        chapter=max(1,min(int(r["chapter"]),len(self.STORY)))
        title,text=self.STORY[chapter-1]
        return f"📖 LOS SANTOS • ТВОЯ ИСТОРИЯ\n\n{title}\n\n{text}\n\n🗺️ Глава {chapter}/{len(self.STORY)} • История продолжается по мере твоих дел."

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

    def sync_milestones(self,uid):
        """Reconcile milestone-style quests from authoritative player state."""
        user=self.db.user(uid)
        rows=self.db.mission_rows(uid,["rich"])
        current=rows.get("rich",{}).get("progress",0)
        if user and int(user["balance"])>=1_000_000 and int(current)<1:
            self.db.mission_add(uid,"rich",1)

    def missions(self,uid):
        self.sync_milestones(uid)
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
        self.sync_milestones(uid)
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
            "🏙️ BANDIT CITY • LOS SANTOS\n\n"
            "Ночной город не встречает новичков фанфарами. Здесь тебя никто не знает — пока ты сам не заставишь говорить о себе.\n\n"
            "🧥 У закусочной тебя замечает парень в кожаной куртке: «Первый совет бесплатно: не гонись за красивой жизнью, пока не научился зарабатывать. Начни с малого — дальше разберёмся».\n\n"
            "💰 Стартовый капитал: $100 000\n"
            "⭐ Уровень: 1\n"
            "📍 Твой город: Los Santos\n"
            f"{bonus_line}\n"
            "🎬 С ЧЕГО НАЧАТЬ\n"
            "1️⃣ 💼 Открой «Работа» и заверши первую смену — получишь деньги и опыт.\n"
            "2️⃣ 🎒 Следи за энергией и голодом: вымотанный игрок далеко не уедет.\n"
            "3️⃣ 🏢 Копи капитал, открывай бизнес и забирай накопленный доход.\n"
            "4️⃣ 🚗 Подбирай машину по карману и постепенно расширяй гараж.\n\n"
            "📖 Сюжетный пролог проведёт тебя по первым шагам один раз. После завершения он исчезнет из меню — город не будет гонять тебя по одной и той же экскурсии.\n\n"
            "🎁 Приглашай друзей, выполняй дела и помни: в Los Santos у каждого решения есть цена.\n\n"
            "👇 Выбирай первый шаг. Посмотрим, кем ты станешь."
        )

    def status(self,uid):
        r=self.db.status(uid)
        wanted="🟢 Низкая" if r["heat"]<25 else ("🟡 Внимание" if r["heat"]<60 else ("🟠 Розыск" if r["heat"]<85 else "🔴 Особо разыскивается"))
        rep="Нейтральная" if r["reputation"]==0 else ("Уважаемый" if r["reputation"]>0 else "Опасный")
        hunger_state="сыт" if r["hunger"]<35 else ("голоден" if r["hunger"]<70 else "очень голоден")
        return f"📊 СТАТУС\n\n⚡ Энергия: {r['energy']}/100\n🍔 Голод: {r['hunger']}/100 — {hunger_state}\n🚨 Розыск: {r['heat']}/100 — {wanted}\n⭐ Репутация: {r['reputation']} — {rep}"

    def eat_item(self,uid,item_id):
        name=self.db.consume_inventory_item(uid,item_id)
        if name is None:
            return "❌ Предмет не найден в твоём инвентаре."
        if name == "":
            return "ℹ️ Этот предмет нельзя использовать как еду или напиток."
        lowered=name.lower()
        # Explicit effects prevent every newly added consumable from becoming
        # an energy drink by default. Values are clamped by Database.status_change.
        if "энергетик" in lowered:
            self.db.status_change(uid,energy=30)
            effect="⚡ Энергия +30"
        elif "кофе" in lowered:
            self.db.status_change(uid,energy=15)
            effect="☕ Энергия +15"
        elif any(word in lowered for word in ("бургер","сэндвич","еда")):
            self.db.status_change(uid,hunger=-35,energy=5)
            effect="🍔 Голод −35 • ⚡ Энергия +5"
        elif "вода" in lowered:
            self.db.status_change(uid,hunger=-5,energy=3)
            effect="💧 Голод −5 • ⚡ Энергия +3"
        else:
            return "ℹ️ Этот предмет нельзя использовать как еду или напиток."
        return f"✅ ИСПОЛЬЗОВАНО: {name}\n\n{effect}"

    def city_events(self, uid):
        import datetime
        from catalog import EVENTS
        from event_announcer import active_events, event_overrides
        from city_news import city_news_feed, daypart_label

        now = datetime.datetime.now(datetime.timezone.utc)
        overrides = event_overrides(self.db)
        active = active_events(self.db, now)
        part = daypart_label(now.hour)
        lines = ["🌆 BANDIT CITY • ГОРОДСКАЯ ЛЕНТА", "🕒 {} • UTC".format(part), ""]
        lines.extend(city_news_feed(now))
        lines.extend(["", "━━━━━━━━━━━━━━━━", "🎪 СОБЫТИЯ И ЭКСКЛЮЗИВЫ", ""])
        if active:
            lines.append("🔥 СЕЙЧАС ПРОХОДЯТ")
            for code, event in active.items():
                lines.extend([str(event.get("title") or code), str(event.get("description") or "Городское событие активно.")])
                goal = event.get("goal_label")
                if goal:
                    lines.append("🎯 Цель: " + str(goal))
                drops = event.get("drops") or []
                if drops:
                    lines.append("🎁 Награда события: " + ", ".join(str(x) for x in drops))
                end_at = event.get("end_at")
                if end_at:
                    try:
                        end = datetime.datetime.fromisoformat(str(end_at).replace("Z", "+00:00"))
                        lines.append("⏳ До: " + end.strftime("%d.%m.%Y %H:%M UTC"))
                    except ValueError:
                        pass
                lines.extend(["📍 Открой событие и проверь цель участия.", ""])
        upcoming = []
        for code, event in EVENTS.items():
            if overrides.get(code) == "off" or code in active or overrides.get(code) == "on":
                continue
            start_at = event.get("start_at")
            if not start_at:
                continue
            try:
                start = datetime.datetime.fromisoformat(str(start_at).replace("Z", "+00:00"))
            except ValueError:
                continue
            if start > now:
                upcoming.append((start, code, event))
        upcoming.sort(key=lambda item: item[0])
        if upcoming:
            lines.extend(["🕒 СКОРО В ГОРОДЕ"])
            for start, code, event in upcoming[:3]:
                lines.append("{} — старт {}".format(event.get("title") or code, start.strftime("%d.%m.%Y %H:%M UTC")))
                lines.append(str(event.get("description") or "Подробности появятся ближе к началу."))
                lines.append("")
        if not active and not upcoming:
            lines.append("Пока нет запланированных крупных ивентов — следи за городской лентой.")
        lines.extend(["📣 Важные старты объявляются игрокам автоматически.", "🗞️ Лента меняется в течение дня; возвращайся за новыми происшествиями."])
        return "\\n".join(lines).strip()

    def profile(self, uid):
        u=self.db.user(uid)
        cars=len(self.db.cars(uid))
        items=len(self.db.items(uid))
        event_rows=self.db.event_history(uid)
        event_count=len(event_rows)
        event_names=[EVENTS.get(r["event_code"],{}).get("title",r["event_code"]) for r in event_rows]
        if event_count >= 10:
            event_badge="👑 Легенда событий"
        elif event_count >= 5:
            event_badge="🔥 Опытный участник"
        elif event_count >= 3:
            event_badge="🏅 Ветеран событий"
        elif event_count >= 1:
            event_badge="🎟️ Участник событий"
        else:
            event_badge="🎟️ Новичок событий"
        return (
            "👤 ПРОФИЛЬ\n\n"
            f"🎭 Ник: {u['nickname']}\n🏙 {u['city']}\n"
            f"💵 Наличные: {money(u['balance'])}\n🏦 Банк: {money(u['bank'])}\n"
            f"⭐ Уровень: {u['level']}\n✨ XP: {u['xp']}\n"
            f"👥 Рефералов: {u['referrals']}\n🚗 Машин: {cars}\n🎒 Вещей: {items}\n\n"
            f"🏆 События: {event_count}\n{event_badge}\n"
            + (f"📜 История: {' • '.join(event_names[-3:])}\n" if event_names else "")
            + f"🔗 Код: {u['ref_code']}"
        )

    def work(self, uid, job):
        if job not in self.JOBS: return "❌ Работа не найдена."
        name,reward,xp=self.JOBS[job]
        now=int(time.time())
        last=self.db.job_last(uid,job)
        if now-last<60:
            return f"⏳ Подожди {60-(now-last)} сек."
        status=self.db.status(uid)
        if int(status["energy"])<10:
            return "😴 Ты вымотан. Отдохни или используй энергетик из инвентаря."
        if int(status["hunger"])>=95:
            return "🍔 Ты слишком голоден, чтобы работать. Купи еду в магазине и используй её из инвентаря."
        self.db.status_change(uid,energy=-10,hunger=3,heat=2,reputation=1)
        self.db.add_money(uid,reward)
        self.db.xp(uid,xp)
        self.db.job_set(uid,job)
        if not self.db.sms_task_rows(uid,["first_job"]).get("first_job",{}).get("completed",0):
            self.db.sms_task_complete(uid,"first_job")
            self.db.sms_add(uid,"📱 Неизвестный номер","Первое дело сделано. Теперь город знает, что ты умеешь работать.","first_job",25000,20)
        self.db.mission_add(uid,"work_3",1)
        self.db.mission_add(uid,"earn_100k",reward)
        self.record_event_action(uid,"work",1)
        after_shift = random.choice([
            "🧥 Проводник кивает: «Неплохо. В городе замечают тех, кто не бросает дело на полпути».",
            "📱 Телефон коротко вибрирует. Похоже, слух о твоей работе уже пошёл по району.",
            "🌃 Смена закончена. Ноги гудят, зато сегодня ты стал чуть ближе к своей цели.",
            "🤝 Кто-то у входа узнаёт тебя и бросает: «Слышал, ты сегодня был при деле. Так держать».",
            "💬 «Первый заработок запомни, — говорит знакомый. — Потом будет с чем сравнить большие деньги»."
        ])
        return f"✅ СМЕНА ЗАВЕРШЕНА • {name}\n💵 Заработано: +{money(reward)}\n✨ Опыт: +{xp} XP\n⚡ Энергия −10 • 🍔 Голод +3\n\n{after_shift}"

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
            self.record_event_action(uid,"buy_business",1)
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
            self.db.mission_add(uid,"ref_1",1)
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
            self.record_event_action(uid,"buy_car",1)
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
                # A pair returns the stake; paying 2x made slots exploitable and
                # incorrectly counted a break-even round as a win.
                payout=bet
                self.db.add_money(uid,payout)
                won=None
                profit=0
                result=f"🎰 {' | '.join(reels)}\n↩️ Пара! Ставка возвращена: {money(payout)}"
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
                won=None
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
