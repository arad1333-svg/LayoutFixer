"""
clipboard_handler.py — Full conversion pipeline:
  save clipboard → copy → convert → paste → restore clipboard → (optionally) switch layout.
"""
import logging
import time
import threading

import pyperclip

from converter import convert
from settings_manager import load as load_settings
import layout_switcher
from plat import (
    save_clipboard,
    restore_clipboard,
    get_clipboard_counter,
    wait_for_clipboard_change,
    release_hotkey_modifiers,
    send_copy,
    send_paste,
)

log = logging.getLogger(__name__)

# Re-entrancy guard: prevents hotkey from firing during paste
_converting = False
_lock = threading.Lock()


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

    saved_clipboard = None
    try:
        # Wait for the OS to finish processing the hotkey press, then release
        # modifier keys so they don't bleed into our simulated copy command.
        time.sleep(0.15)
        release_hotkey_modifiers()
        time.sleep(0.05)

        # 1. Save current clipboard
        saved_clipboard = save_clipboard()
        initial_counter = get_clipboard_counter()

        # 2. Simulate copy (Ctrl+C on Windows, Cmd+C on macOS)
        send_copy()

        # 3. Wait for clipboard to update
        changed = wait_for_clipboard_change(initial_counter, timeout_ms=max(delay_ms * 5, 500))
        if not changed:
            log.warning('Clipboard did not change after copy — nothing selected?')
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
        from converter import _detect_direction
        detected_direction = _detect_direction(text)
        converted = convert(text, detected_direction, custom_keymap=custom_keymap)

        if converted == text:
            log.debug('Converted text is identical to original — no change')
            return

        # 6. Write converted text to clipboard
        pyperclip.copy(converted)

        # 7. Simulate paste (Ctrl+V on Windows, Cmd+V on macOS)
        send_paste()

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
        # Always restore original clipboard
        if saved_clipboard is not None:
            try:
                restore_clipboard(saved_clipboard)
            except Exception:
                log.debug('restore clipboard failed', exc_info=True)
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
