"""Russian role-aware admin UI strings for Bandit City.

Handlers can consume these factories without duplicating permission rules.
"""

from roles import Role, ROLE_LABELS


class RoleUI:
    def __init__(self, roles):
        self.roles = roles

    def main_button(self, vk_id):
        role = self.roles.role(vk_id)
        if role == Role.OWNER:
            return "👑 Центр владельца"
        if role == Role.ADMIN:
            return "⚙️ Панель администратора"
        if role == Role.MODERATOR:
            return "🛡 Панель модератора"
        return None

    def home(self, vk_id):
        role = self.roles.role(vk_id)
        if role == Role.OWNER:
            return (
                "👑 BANDIT CITY • ЦЕНТР ВЛАДЕЛЬЦА\n\n"
                "Полный контроль проекта и персонала.\n\n"
                "👥 ПЕРСОНАЛ\n"
                "➕ Выдать роль\n"
                "🔄 Изменить роль\n"
                "➖ Снять роль\n"
                "📋 Список персонала\n"
                "🧾 Журнал ролей\n\n"
                "🏙️ ГОРОД\n"
                "📊 Статистика\n"
                "⚙️ Технический режим\n"
                "🎪 Ивенты\n"
                "📢 Рассылка"
            ), [
                ["➕ Выдать роль", "🔄 Изменить роль"],
                ["➖ Снять роль", "📋 Список персонала"],
                ["🧾 Журнал ролей"],
                ["📊 Статистика", "⚙️ Технический режим"],
                ["🎪 Ивенты", "📢 Рассылка"],
                ["🏙️ Главное меню"],
            ]
        if role == Role.ADMIN:
            return (
                "⚙️ BANDIT CITY • ПАНЕЛЬ АДМИНИСТРАТОРА\n\n"
                "Доступны игровые системы, экономика и управление городом.\n\n"
                "🔒 Управление персоналом доступно только владельцу."
            ), [
                ["📊 Статистика", "👥 Игроки"],
                ["💰 Экономика", "⭐ XP / Уровень"],
                ["🏢 Бизнес", "🚗 Машины"],
                ["🎒 Вещи", "🛡 Безопасность"],
                ["🎟 Промокоды", "📢 Рассылка"],
                ["🎨 Внешность", "🎪 Ивенты"],
                ["⚙️ Технический режим"],
                ["🏙️ Главное меню"],
            ]
        if role == Role.MODERATOR:
            return (
                "🛡 BANDIT CITY • ПАНЕЛЬ МОДЕРАТОРА\n\n"
                "Контроль игроков, нарушения и журнал модерации.\n\n"
                "🔒 Экономика и управление персоналом недоступны."
            ), [
                ["👥 Игроки", "🛡 Безопасность"],
                ["🧾 Журнал"],
                ["🏙️ Главное меню"],
            ]
        return "", []

    def staff_list(self):
        staff = self.roles.staff()
        if not staff:
            return "📋 ПЕРСОНАЛ\n\nПока нет назначенных сотрудников."
        lines = ["📋 ПЕРСОНАЛ", ""]
        for item in staff:
            lines.append(f"{ROLE_LABELS[item.role]} • VK {item.vk_id}")
        return "\n".join(lines)

    @staticmethod
    def role_choices():
        return [
            ["⚙️ Администратор"],
            ["🛡 Модератор"],
            ["👤 Игрок"],
            ["👑 Центр владельца"],
        ]

    @staticmethod
    def parse_role(text):
        return {
            "⚙️ Администратор": Role.ADMIN,
            "🛡 Модератор": Role.MODERATOR,
            "👤 Игрок": Role.PLAYER,
        }.get(text.strip())
