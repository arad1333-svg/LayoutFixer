"""
plat/clipboard_mac.py — macOS clipboard save/restore and key simulation.

Phase 0: pyperclip handles plain-text save/restore (text-only simplification
for v1). Quartz key simulation is stubbed — Phase 1 fills these in on Mac.

Only imported on sys.platform == 'darwin'.
"""
import logging
import time

import pyperclip

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Clipboard save / restore (text-only for Phase 1)
# ---------------------------------------------------------------------------

def save_clipboard() -> str:
    """Return current clipboard contents as a plain string."""
    try:
        return pyperclip.paste() or ''
    except Exception:
        log.exception('Failed to save clipboard')
        return ''


def restore_clipboard(saved: str) -> None:
    """Restore previously saved clipboard contents."""
    if not saved:
        return
    try:
        pyperclip.copy(saved)
    except Exception:
        log.exception('Failed to restore clipboard')


# ---------------------------------------------------------------------------
# Clipboard change count (NSPasteboard.changeCount)
# ---------------------------------------------------------------------------

def get_clipboard_counter() -> int:
    """Return the current NSPasteboard change count."""
    try:
        from AppKit import NSPasteboard  # type: ignore[import]
        return NSPasteboard.generalPasteboard().changeCount()
    except Exception:
        log.warning('get_clipboard_counter: AppKit unavailable — returning 0')
        return 0


def wait_for_clipboard_change(initial_counter: int, timeout_ms: int = 500) -> bool:
    """Poll NSPasteboard.changeCount until it differs from initial_counter."""
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        if get_clipboard_counter() != initial_counter:
            return True
        time.sleep(0.01)
    return False


# ---------------------------------------------------------------------------
# Key simulation via Quartz CGEventPost
# ---------------------------------------------------------------------------

def release_hotkey_modifiers() -> None:
    """
    Release Cmd, Option, Shift, Ctrl modifier keys after the Globe double-tap.

    Key-up events are injected for each modifier so they don't bleed into
    the subsequent Cmd+C simulation.
    """
    try:
        import Quartz  # type: ignore[import]
        # Virtual key codes: Cmd=55, Option=58, Shift=56, Ctrl=59
        for vk in (55, 58, 56, 59):
            event = Quartz.CGEventCreateKeyboardEvent(None, vk, False)  # key-up
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
    except Exception:
        log.exception('release_hotkey_modifiers failed')


def _send_cmd_key(key_vk: int) -> None:
    """Simulate Cmd+key via CGEventPost."""
    try:
        import Quartz  # type: ignore[import]
        kCGEventFlagMaskCommand = Quartz.kCGEventFlagMaskCommand

        # key down
        ev_down = Quartz.CGEventCreateKeyboardEvent(None, key_vk, True)
        Quartz.CGEventSetFlags(ev_down, kCGEventFlagMaskCommand)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev_down)

        # key up
        ev_up = Quartz.CGEventCreateKeyboardEvent(None, key_vk, False)
        Quartz.CGEventSetFlags(ev_up, kCGEventFlagMaskCommand)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev_up)
    except Exception:
        log.exception('_send_cmd_key(%d) failed', key_vk)


def send_copy() -> None:
    """Simulate Cmd+C to copy the current selection."""
    _send_cmd_key(8)  # virtual key code 8 = 'c'


def send_paste() -> None:
    """Simulate Cmd+V to paste clipboard content."""
    _send_cmd_key(9)  # virtual key code 9 = 'v'
