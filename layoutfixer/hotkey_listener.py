"""
hotkey_listener.py — Global hotkey registration via pynput.

Supports re-registration when the user changes the hotkey in settings.
"""
import logging
import threading
from typing import Callable

from pynput import keyboard

log = logging.getLogger(__name__)


class HotkeyListener:
    """
    Manages a single global hotkey that calls a callback when pressed.

    Re-register by calling stop() followed by start() with a new hotkey string,
    or use update_hotkey() which does both atomically.
    """

    def __init__(self, hotkey: str, callback: Callable[[], None]) -> None:
        self._hotkey = hotkey
        self._callback = callback
        self._listener: keyboard.GlobalHotKeys | None = None
        self._suspended = False
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start listening for the hotkey (blocking registration, non-blocking listener)."""
        with self._lock:
            self._stop_listener()
            self._start_listener()

    def stop(self) -> None:
        """Stop listening."""
        with self._lock:
            self._stop_listener()

    def update_hotkey(self, new_hotkey: str) -> bool:
        """Atomically replace the current hotkey with a new one.

        Returns True on success, False if registration failed (reverts to old hotkey).
        """
        with self._lock:
            old_hotkey = self._hotkey
            self._stop_listener()
            self._hotkey = new_hotkey
            if not self._suspended:
                try:
                    self._start_listener()
                except Exception:
                    log.warning(
                        'Failed to register hotkey %s, reverting to %s',
                        new_hotkey, old_hotkey, exc_info=True,
                    )
                    self._hotkey = old_hotkey
                    try:
                        self._start_listener()
                    except Exception:
                        log.error('Failed to restore previous hotkey %s', old_hotkey, exc_info=True)
                    return False
        log.info('Hotkey updated to: %s', new_hotkey)
        return True

    def suspend(self) -> None:
        """Temporarily disable the hotkey without forgetting it."""
        with self._lock:
            if not self._suspended:
                self._stop_listener()
                self._suspended = True
        log.info('Hotkey suspended')

    def resume(self) -> None:
        """Re-enable a suspended hotkey."""
        with self._lock:
            if self._suspended:
                self._suspended = False
                self._start_listener()
        log.info('Hotkey resumed')

    @property
    def is_suspended(self) -> bool:
        return self._suspended

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _start_listener(self) -> None:
        """Create and start a GlobalHotKeys listener (called under lock)."""
        pynput_hotkey = _to_pynput_hotkey(self._hotkey)
        self._listener = keyboard.GlobalHotKeys({pynput_hotkey: self._on_hotkey})
        self._listener.start()
        log.info('Hotkey listener started: %s → %s', self._hotkey, pynput_hotkey)

    def _stop_listener(self) -> None:
        """Stop and discard the current listener (called under lock)."""
        if self._listener is None:
            return
        try:
            self._listener.stop()
            self._listener.join(timeout=2.0)
        except Exception:
            log.warning('stop listener error', exc_info=True)
        self._listener = None

    def _on_hotkey(self) -> None:
        """Called by pynput on hotkey press — dispatches callback in a worker thread."""
        if self._suspended:
            return
        log.debug('Hotkey pressed: %s', self._hotkey)
        # Run callback in a daemon thread so pynput's listener thread isn't blocked
        t = threading.Thread(target=self._callback, daemon=True, name='hotkey-callback')
        t.start()


# ---------------------------------------------------------------------------
# Hotkey string conversion: "ctrl+alt+z" → pynput format "<ctrl>+<alt>+z"
# ---------------------------------------------------------------------------

_MODIFIER_MAP = {
    'ctrl': '<ctrl>',
    'control': '<ctrl>',
    'alt': '<alt>',
    'shift': '<shift>',
    'cmd': '<cmd>',
    'win': '<cmd>',
}


def _to_pynput_hotkey(hotkey: str) -> str:
    """
    Convert a human-readable hotkey string to pynput GlobalHotKeys format.

    Examples:
        'ctrl+alt+z' → '<ctrl>+<alt>+z'
        'ctrl+shift+f' → '<ctrl>+<shift>+f'
    """
    parts = [p.strip().lower() for p in hotkey.split('+')]
    converted = []
    for part in parts:
        if part in _MODIFIER_MAP:
            converted.append(_MODIFIER_MAP[part])
        else:
            converted.append(part)
    return '+'.join(converted)
