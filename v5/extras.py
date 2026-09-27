"""Compatibility entry points for the V5 UI."""
from .bridge import (
    character,
    clothing_catalog,
    clothing_menu,
    inventory,
    item_shop,
    premium_shop,
    shop_hub,
    weapon_shop,
)

__all__ = [
    "character", "clothing_catalog", "clothing_menu", "inventory",
    "item_shop", "premium_shop", "shop_hub", "weapon_shop",
]
