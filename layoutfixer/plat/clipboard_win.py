"""
plat/clipboard_win.py — Windows clipboard save/restore and key simulation.

Extracted from clipboard_handler.py. All functions use win32clipboard and
ctypes.windll.user32 (Windows-only). Only imported on sys.platform == 'win32'.
"""
import ctypes
import ctypes.wintypes as wt
import logging
import time

import win32clipboard

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Clipboard save / restore (all formats)
# ---------------------------------------------------------------------------

def save_clipboard() -> dict:
    """Read all clipboard formats and return them as {format_id: data}."""
    saved: dict[int, bytes] = {}
    try:
        win32clipboard.OpenClipboard()
        fmt = win32clipboard.EnumClipboardFormats(0)
        while fmt:
            try:
                data = win32clipboard.GetClipboardData(fmt)
                saved[fmt] = data
            except Exception:
                pass  # Some formats can't be read directly — skip
            fmt = win32clipboard.EnumClipboardFormats(fmt)
    except Exception:
        log.exception('Failed to save clipboard')
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass
    return saved


def restore_clipboard(saved: dict) -> None:
    """Write previously saved clipboard contents back, preserving all formats."""
    if not saved:
        return
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        for fmt, data in saved.items():
            try:
                win32clipboard.SetClipboardData(fmt, data)
            except Exception:
                pass  # Some formats may not be settable directly
    except Exception:
        log.exception('Failed to restore clipboard')
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Clipboard sequence number
# ---------------------------------------------------------------------------

def get_clipboard_counter() -> int:
    """Return the current Windows clipboard sequence number."""
    return win32clipboard.GetClipboardSequenceNumber()


def wait_for_clipboard_change(initial_counter: int, timeout_ms: int = 500) -> bool:
    """Poll until the clipboard sequence number changes or timeout elapses."""
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        if win32clipboard.GetClipboardSequenceNumber() != initial_counter:
            return True
        time.sleep(0.01)
    return False


# ---------------------------------------------------------------------------
# Key simulation
# ---------------------------------------------------------------------------

def release_hotkey_modifiers() -> None:
    """
    Explicitly release Ctrl, Alt, and Shift keys.

    When the hotkey (e.g. Ctrl+Alt+Z) fires, those modifier keys are still
    physically/logically pressed. Releasing them first ensures a clean Ctrl+C.
    """
    KEYEVENTF_KEYUP = 0x0002
    for vk in (0x11, 0x12, 0x10):  # VK_CONTROL, VK_MENU (Alt), VK_SHIFT
        ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ('wVk', wt.WORD), ('wScan', wt.WORD), ('dwFlags', wt.DWORD),
        ('time', wt.DWORD), ('dwExtraInfo', ctypes.POINTER(wt.ULONG)),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [('ki', _KEYBDINPUT), ('padding', ctypes.c_byte * 32)]


class _INPUT(ctypes.Structure):
    _fields_ = [('type', wt.DWORD), ('_input', _INPUT_UNION)]


_INPUT_KEYBOARD = 1
_KEYEVENTF_KEYUP = 0x0002
_VK_CONTROL = 0x11


def _send_ctrl_key(key_char: str) -> None:
    """Simulate Ctrl+key via SendInput."""
    key_vk = ord(key_char.upper())

    def make_key(vk, flags=0):
        inp = _INPUT()
        inp.type = _INPUT_KEYBOARD
        inp._input.ki.wVk = vk
        inp._input.ki.dwFlags = flags
        return inp

    inputs = (_INPUT * 4)(
        make_key(_VK_CONTROL),
        make_key(key_vk),
        make_key(key_vk, _KEYEVENTF_KEYUP),
        make_key(_VK_CONTROL, _KEYEVENTF_KEYUP),
    )
    ctypes.windll.user32.SendInput(4, inputs, ctypes.sizeof(_INPUT))


def send_copy() -> None:
    """Simulate Ctrl+C to copy the current selection."""
    _send_ctrl_key('c')


def send_paste() -> None:
    """Simulate Ctrl+V to paste clipboard content."""
    _send_ctrl_key('v')
