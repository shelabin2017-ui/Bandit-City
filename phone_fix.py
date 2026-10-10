"""Fix phone contact input so VK profile URLs reach the resolver unchanged."""


def apply(bot):
    original_process_input = bot.process_input

    def process_input(uid, text):
        state = bot.INPUT_STATE.get(uid, {})
        if state.get("mode") == "phone_add":
            value = str(text or "").strip()
            if value.lower() in ("отмена", "❌ отмена", "/cancel"):
                bot.clear_state(uid)
                bot.send_card(uid, "❌ Операция отменена.", bot.main_kb(uid))
                return True

            # Do not cast input to int here: Database.phone_add resolves
            # VK IDs, @nicknames and full VK profile URLs itself.
            player = bot.db.get_or_create_user(uid)
            message = bot.game.phone_add(player["id"], value)
            bot.clear_state(uid)
            bot.send(uid, message, bot.kb_phone())
            return True

        return original_process_input(uid, text)

    bot.process_input = process_input
