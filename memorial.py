"""Persistent one-time memorial announcement for Bandit City."""
import logging

from release import announce_release


MEMORIAL_RELEASE_ID = "memorial-stas-2026-10-28"
MEMORIAL_MESSAGE = """🕯 МИНУТА МОЛЧАНИЯ — В ПАМЯТЬ О СТАСЕ

Сегодня официально подтверждена гибель Стаса, родившегося 23 февраля 2003 года. С 18 октября он числился без вести пропавшим.

BANDIT CITY выражает искренние соболезнования родным, близким и всем, кто знал Стаса.

Просим каждого игрока остановиться хотя бы на минуту и почтить его память молчанием.

Светлая память, Стас. Помним. Скорбим."""


def announce_memorial(db, vk, group_id):
    """Send a persistent, resumable memorial announcement to eligible players."""
    try:
        result = announce_release(
            db,
            vk,
            group_id,
            MEMORIAL_RELEASE_ID,
            MEMORIAL_MESSAGE,
        )
        logging.info("Stas memorial announcement finished: %s", result)
        return result
    except Exception:
        logging.exception("Failed to send Stas memorial announcement")
        return None
