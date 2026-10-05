"""Bandit City role hierarchy and permission core.

This module is intentionally independent from the bot handlers so the live VPS
can adopt it only after the permission tests pass.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable


class Role(IntEnum):
    PLAYER = 0
    MODERATOR = 10
    ADMIN = 20
    OWNER = 30


ROLE_LABELS = {
    Role.PLAYER: "👤 Игрок",
    Role.MODERATOR: "🛡 Модератор",
    Role.ADMIN: "⚙️ Администратор",
    Role.OWNER: "👑 Владелец",
}


PERMISSIONS = {
    "player.read_self": Role.PLAYER,
    "moderation.view_players": Role.MODERATOR,
    "moderation.ban": Role.MODERATOR,
    "moderation.unban": Role.MODERATOR,
    "moderation.view_logs": Role.MODERATOR,
    "economy.manage": Role.ADMIN,
    "xp.manage": Role.ADMIN,
    "business.manage": Role.ADMIN,
    "cars.manage": Role.ADMIN,
    "items.manage": Role.ADMIN,
    "promos.manage": Role.ADMIN,
    "broadcast.send": Role.ADMIN,
    "events.manage": Role.ADMIN,
    "maintenance.manage": Role.ADMIN,
    "appearance.manage": Role.ADMIN,
    "staff.view": Role.OWNER,
    "staff.grant": Role.OWNER,
    "staff.change": Role.OWNER,
    "staff.revoke": Role.OWNER,
    "owner.manage": Role.OWNER,
}


@dataclass(frozen=True)
class StaffRecord:
    vk_id: int
    role: Role
    assigned_by: int | None
    assigned_at: int


class RoleManager:
    """SQLite-backed role manager.

    The manager creates only its own tables and never rewrites player data.
    OWNER is protected from modification by every lower role.
    """

    def __init__(self, db):
        self.db = db
        self._init_schema()

    def _init_schema(self):
        with self.db.connect() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS user_roles(
                    vk_id INTEGER PRIMARY KEY,
                    role INTEGER NOT NULL DEFAULT 0,
                    assigned_by INTEGER,
                    assigned_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS role_logs(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_vk INTEGER NOT NULL,
                    target_vk INTEGER,
                    action TEXT NOT NULL,
                    old_role INTEGER,
                    new_role INTEGER,
                    created_at INTEGER NOT NULL
                );
                """
            )

    @staticmethod
    def _now() -> int:
        return int(time.time())

    @staticmethod
    def parse_ids(value: str | None) -> set[int]:
        if not value:
            return set()
        result = set()
        for part in value.replace(";", ",").split(","):
            part = part.strip()
            if part.isdigit():
                result.add(int(part))
        return result

    def ensure_player(self, vk_id: int) -> Role:
        vk_id = int(vk_id)
        with self.db.connect() as c:
            row = c.execute("SELECT role FROM user_roles WHERE vk_id=?", (vk_id,)).fetchone()
            if row:
                return Role(int(row["role"]))
            c.execute(
                "INSERT INTO user_roles(vk_id,role,assigned_by,assigned_at) VALUES(?,?,?,?)",
                (vk_id, int(Role.PLAYER), None, self._now()),
            )
            return Role.PLAYER

    def role(self, vk_id: int) -> Role:
        return self.ensure_player(vk_id)

    def has(self, vk_id: int, permission: str) -> bool:
        required = PERMISSIONS.get(permission)
        if required is None:
            return False
        return self.role(vk_id) >= required

    def can_manage_role(self, actor_vk: int, target_vk: int, new_role: Role) -> tuple[bool, str]:
        actor = self.role(actor_vk)
        target = self.role(target_vk)
        new_role = Role(int(new_role))

        if actor < Role.OWNER:
            return False, "❌ Только владелец может управлять персоналом."
        if int(actor_vk) == int(target_vk) and new_role != Role.OWNER:
            return False, "❌ Владелец не может снять роль с самого себя."
        if target == Role.OWNER and int(actor_vk) != int(target_vk):
            return False, "❌ Роль владельца защищена."
        if new_role == Role.OWNER and int(actor_vk) != int(target_vk):
            return False, "❌ Нельзя передать роль владельца через эту операцию."
        return True, "OK"

    def set_role(self, actor_vk: int, target_vk: int, new_role: Role) -> tuple[bool, str]:
        actor_vk = int(actor_vk)
        target_vk = int(target_vk)
        new_role = Role(int(new_role))
        ok, reason = self.can_manage_role(actor_vk, target_vk, new_role)
        if not ok:
            return False, reason

        old_role = self.role(target_vk)
        now = self._now()
        with self.db.connect() as c:
            c.execute(
                "INSERT INTO user_roles(vk_id,role,assigned_by,assigned_at) VALUES(?,?,?,?) "
                "ON CONFLICT(vk_id) DO UPDATE SET role=excluded.role, assigned_by=excluded.assigned_by, assigned_at=excluded.assigned_at",
                (target_vk, int(new_role), actor_vk, now),
            )
            c.execute(
                "INSERT INTO role_logs(actor_vk,target_vk,action,old_role,new_role,created_at) VALUES(?,?,?,?,?,?)",
                (actor_vk, target_vk, "set_role", int(old_role), int(new_role), now),
            )
        return True, f"✅ Роль изменена: {ROLE_LABELS[old_role]} → {ROLE_LABELS[new_role]}"

    def revoke(self, actor_vk: int, target_vk: int) -> tuple[bool, str]:
        return self.set_role(actor_vk, target_vk, Role.PLAYER)

    def staff(self) -> list[StaffRecord]:
        with self.db.connect() as c:
            rows = c.execute(
                "SELECT vk_id,role,assigned_by,assigned_at FROM user_roles WHERE role>? ORDER BY role DESC, vk_id",
                (int(Role.PLAYER),),
            ).fetchall()
        return [
            StaffRecord(int(r["vk_id"]), Role(int(r["role"])), r["assigned_by"], int(r["assigned_at"]))
            for r in rows
        ]

    def bootstrap_owner(self, owner_vk: int) -> None:
        """Idempotently marks the project owner.

        Intended for a one-time deployment step using a trusted OWNER_VK_ID
        environment variable. It does not expose or print the ID.
        """
        owner_vk = int(owner_vk)
        with self.db.connect() as c:
            now = self._now()
            c.execute(
                "INSERT INTO user_roles(vk_id,role,assigned_by,assigned_at) VALUES(?,?,?,?) "
                "ON CONFLICT(vk_id) DO UPDATE SET role=?, assigned_by=?, assigned_at=?",
                (owner_vk, int(Role.OWNER), owner_vk, now, int(Role.OWNER), owner_vk, now),
            )

    def bootstrap_from_env(self) -> int:
        """Bootstrap OWNER_VK_ID if configured; return number of changes."""
        raw = os.getenv("OWNER_VK_ID", "").strip()
        if not raw.isdigit():
            return 0
        self.bootstrap_owner(int(raw))
        return 1

    def is_admin_compat(self, vk_id: int, legacy_admin_ids: Iterable[int]) -> bool:
        """Compatibility helper while old ADMIN_IDS handlers are migrated."""
        return self.role(vk_id) >= Role.ADMIN or int(vk_id) in {int(x) for x in legacy_admin_ids}

    @staticmethod
    def label(role: Role) -> str:
        return ROLE_LABELS[Role(int(role))]
