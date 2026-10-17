"""Bandit City V5 compatibility layer."""
from . import bridge

if hasattr(bridge, "EVENT_CLOTHING"):
    bridge.CLOTHING = {**bridge.CLOTHING, **bridge.EVENT_CLOTHING}
