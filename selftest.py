import os
import tempfile
import unittest

from catalog import EVENT_EXCLUSIVES, public_catalog, active_events
from db import Database
from admin_panel import AdminPanel
from roles import Role, RoleManager


class BanditCoreTest(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mktemp(suffix=".db")
        self.db = Database(self.path)

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.path + suffix)
            except FileNotFoundError:
                pass

    def test_schema_settings_and_integrity(self):
        self.assertEqual(self.db.get_setting("missing", "0"), "0")
        self.db.set_setting("maintenance_mode", "1")
        self.assertTrue(self.db.maintenance_mode())
        with self.db.connect() as c:
            self.assertEqual(c.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_all_secret_event_promos(self):
        import v5
        user = self.db.get_or_create_user(100004)
        for code, item in (
            ("FOUNDER-2026", "🧥 Founder Jacket"),
            ("NEON-2026", "🌃 Neon City Background"),
            ("BLACKOUT-2026", "⛓ Blackout Chain"),
            ("ANNIVERSARY-2026", "🏆 Bandit Legend Outfit"),
            ("NIGHTFALL-X", "🎭 Nightfall Mask"),
            ("PRIME-2026", "👑 Prime Hair"),
            ("GOLDEN-2026", "🔫 Golden Bullet"),
        ):
            ok, message = self.db.redeem_promo(user["id"], code)
            self.assertTrue(ok, (code, message))
        with self.db.connect() as c:
            names = {r["name"] for r in c.execute(
                "SELECT name FROM v5_wardrobe WHERE user_id=? AND category='🎪 Ивент • Эксклюзивы'",
                (user["id"],),
            )}
        self.assertTrue({
            "🧥 Founder Jacket","🌃 Neon City Background","⛓ Blackout Chain",
            "🏆 Bandit Legend Outfit","🎭 Nightfall Mask","👑 Prime Hair","🔫 Golden Bullet"
        }.issubset(names))

    def test_event_promo_is_not_public(self):
        import v5
        user = self.db.get_or_create_user(100001)
        ok, message = self.db.redeem_promo(user["id"], "FOUNDER-2026")
        self.assertTrue(ok, message)
        with self.db.connect() as c:
            row = c.execute(
                "SELECT 1 FROM v5_wardrobe WHERE user_id=? AND name=?",
                (user["id"], "🧥 Founder Jacket"),
            ).fetchone()
        self.assertIsNotNone(row)
        public_names = {
            item["name"]
            for section in public_catalog().values()
            for item in section
        }
        self.assertNotIn("🧥 Founder Jacket", public_names)

    def test_event_exclusive_buttons_are_rendered(self):
        from v5 import bridge as v5
        user = self.db.get_or_create_user(100005)
        self.db.redeem_promo(user["id"], "FOUNDER-2026")
        message, buttons = v5.clothing_catalog(self.db, user["vk_id"], "🎪 Ивент • Эксклюзивы")
        self.assertIn("Founder Jacket", message)
        self.assertIn(["✅ 🧥 Founder Jacket"], buttons)

    def test_event_catalog_is_separate(self):
        self.assertEqual(len(EVENT_EXCLUSIVES), 7)
        self.assertGreaterEqual(len(active_events()), 1)

    def test_schema_columns_and_admin_import(self):
        with self.db.connect() as c:
            tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertTrue({'users','cars','items','promo_codes','promo_redemptions','user_appearance'}.issubset(tables))
            required_map = {
                'cars': {'id','user_id','model','category','speed','price','bought_at'},
                'items': {'id','user_id','name','price','bought_at'},
                'promo_codes': {'code','reward_cash','reward_xp','reward_item','reward_slot','max_uses','used_count','active'},
                'user_appearance': {'user_id','hair','clothes','pants','shoes','head','accessory','background','updated_at'},
            }
            for table, required in required_map.items():
                cols = {r[1] for r in c.execute(f"PRAGMA table_info({table})")}
                self.assertTrue(required.issubset(cols), (table, required - cols))
        panel = AdminPanel(self.db, None, {999})
        self.assertTrue(panel.is_admin(999))
        self.assertFalse(panel.is_admin(998))


    def test_role_hierarchy_and_protection(self):
        roles = RoleManager(self.db)
        owner, admin, moderator, player = 9001, 9002, 9003, 9004
        roles.bootstrap_owner(owner)
        ok, _ = roles.set_role(owner, admin, Role.ADMIN)
        self.assertTrue(ok)
        ok, _ = roles.set_role(owner, moderator, Role.MODERATOR)
        self.assertTrue(ok)
        self.assertTrue(roles.has(owner, "owner.manage"))
        self.assertTrue(roles.has(admin, "economy.manage"))
        self.assertTrue(roles.has(moderator, "moderation.ban"))
        self.assertFalse(roles.has(moderator, "economy.manage"))
        ok, _ = roles.set_role(admin, player, Role.ADMIN)
        self.assertFalse(ok)
        ok, _ = roles.revoke(admin, owner)
        self.assertFalse(ok)

    def test_attack_runtime(self):
        a = self.db.get_or_create_user(100002)
        b = self.db.get_or_create_user(100003)
        with self.db.connect() as c:
            c.execute("UPDATE users SET level=2 WHERE id=?", (a["id"],))
        result = self.db.attack(a["id"], b["vk_id"], "scam")
        self.assertIsInstance(result, str)


if __name__ == "__main__":
    unittest.main(verbosity=2)
