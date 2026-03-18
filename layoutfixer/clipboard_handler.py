"""
clipboard_handler.py — Full conversion pipeline:
  save clipboard → Ctrl+C → convert → paste → restore clipboard → (optionally) switch layout.
"""
import logging
import time
import threading
import win32clipboard
import win32con
import pyperclip

from converter import convert
from settings_manager import load as load_settings
import layout_switcher

log = logging.getLogger(__name__)

# Re-entrancy guard: prevents hotkey from firing during paste
_converting = False
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Clipboard save / restore (all formats)
# ---------------------------------------------------------------------------

def _save_clipboard() -> dict:
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


def _restore_clipboard(saved: dict) -> None:
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
# Clipboard sequence number polling
# ---------------------------------------------------------------------------

def _wait_for_clipboard_change(initial_seq: int, timeout_ms: int = 500) -> bool:
    """Poll until the clipboard sequence number changes or timeout elapses."""
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        if win32clipboard.GetClipboardSequenceNumber() != initial_seq:
            return True
        time.sleep(0.01)
    return False


# ---------------------------------------------------------------------------
# Key simulation
# ---------------------------------------------------------------------------

def _release_hotkey_modifiers() -> None:
    """
    Explicitly release Ctrl, Alt, and Shift keys.

    When our hotkey (e.g. Ctrl+Alt+Z) fires, those modifier keys are still
    physically/logically pressed. If we send Ctrl+C immediately, the OS sees
    Ctrl+Alt+C instead — which does nothing (and may trigger NVIDIA overlay).
    Releasing modifiers first ensures a clean Ctrl+C.
    """
    import ctypes
    KEYEVENTF_KEYUP = 0x0002
    for vk in (0x11, 0x12, 0x10):  # VK_CONTROL, VK_MENU (Alt), VK_SHIFT
        ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def _send_ctrl(key: str) -> None:
    """Simulate Ctrl+key via SendInput (more reliable than keybd_event)."""
    import ctypes
    import ctypes.wintypes as wt

    KEYEVENTF_KEYUP = 0x0002
    INPUT_KEYBOARD = 1

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ('wVk', wt.WORD), ('wScan', wt.WORD), ('dwFlags', wt.DWORD),
            ('time', wt.DWORD), ('dwExtraInfo', ctypes.POINTER(wt.ULONG)),
        ]

    class _INPUT_UNION(ctypes.Union):
        _fields_ = [('ki', KEYBDINPUT), ('padding', ctypes.c_byte * 32)]

    class INPUT(ctypes.Structure):
        _fields_ = [('type', wt.DWORD), ('_input', _INPUT_UNION)]

    VK_CONTROL = 0x11
    key_vk = ord(key.upper())

    def make_key(vk, flags=0):
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp._input.ki.wVk = vk
        inp._input.ki.dwFlags = flags
        return inp

    inputs = (INPUT * 4)(
        make_key(VK_CONTROL),
        make_key(key_vk),
        make_key(key_vk, KEYEVENTF_KEYUP),
        make_key(VK_CONTROL, KEYEVENTF_KEYUP),
    )
    ctypes.windll.user32.SendInput(4, inputs, ctypes.sizeof(INPUT))


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_conversion() -> None:
    """
    Execute the full conversion pipeline. Safe to call from any thread.
    Guards against re-entrancy.
    """
    global _converting

    with _lock:
        if _converting:
            log.debug('Conversion already in progress — skipping')
            return
        _converting = True

    settings = load_settings()
    delay_ms = settings.get('clipboard_delay_ms', 100)
    custom_keymap = settings.get('custom_keymap') or None
    auto_switch = settings.get('auto_switch_layout', True)

    saved_clipboard: dict = {}
    try:
        # Wait for the OS to finish processing the hotkey press, then release
        # modifier keys so they don't bleed into our simulated Ctrl+C.
        time.sleep(0.15)
        _release_hotkey_modifiers()
        time.sleep(0.05)

        # 1. Save current clipboard
        saved_clipboard = _save_clipboard()
        initial_seq = win32clipboard.GetClipboardSequenceNumber()

        # 2. Simulate Ctrl+C to copy selection
        _send_ctrl('c')

        # 3. Wait for clipboard to update
        changed = _wait_for_clipboard_change(initial_seq, timeout_ms=max(delay_ms * 5, 500))
        if not changed:
            log.warning('Clipboard did not change after Ctrl+C — nothing selected?')
            _notify('LayoutFixer: Select text first, then press the hotkey.', settings)
            return

        # Small extra delay for slow apps (e.g. LibreOffice)
        time.sleep(delay_ms / 1000)

        # 4. Read text
        try:
            text = pyperclip.paste()
        except Exception:
            log.exception('Failed to read clipboard text')
            return

        if not text or not text.strip():
            log.debug('Clipboard text is empty or whitespace — nothing to convert')
            return

        # 5. Convert
        direction = convert.__module__  # warm module cache
        from converter import _detect_direction
        detected_direction = _detect_direction(text)
        converted = convert(text, 'auto', custom_keymap=custom_keymap)

        if converted == text:
            log.debug('Converted text is identical to original — no change')
            return

        # 6. Write converted text to clipboard
        pyperclip.copy(converted)

        # 7. Simulate Ctrl+V to paste
        _send_ctrl('v')

        # 8. Wait for paste to complete
        time.sleep(max(delay_ms, 50) / 1000)

        # 9. Switch layout if enabled
        if auto_switch:
            layout_switcher.switch(detected_direction)

        log.debug('Conversion complete: %r → %r (%s)', text[:30], converted[:30], detected_direction)

    except Exception:
        log.exception('Unexpected error in conversion pipeline')
        _notify('LayoutFixer encountered an error. Please try again.', settings)

    finally:
        # 9. Always restore original clipboard
        _restore_clipboard(saved_clipboard)
        with _lock:
            _converting = False


# ---------------------------------------------------------------------------
# Tray notification helper (imported lazily to avoid circular imports)
# ---------------------------------------------------------------------------

def _notify(message: str, settings: dict) -> None:
    if not settings.get('show_notifications', True):
        return
    try:
        from tray_app import show_notification
        show_notification(message)
    except Exception:
        log.debug('Could not show tray notification: %s', message)
