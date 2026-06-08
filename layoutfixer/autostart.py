"""
autostart.py — Thin facade over plat.autostart_enable / disable / is_enabled.
"""
from plat import (  # noqa: F401
    autostart_enable as enable,
    autostart_disable as disable,
    autostart_is_enabled as is_enabled,
)
