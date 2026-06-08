"""
hotkey_listener.py — Global hotkey registration via pynput.

Windows: keyboard shortcut (e.g. Ctrl+Alt+Z) via GlobalHotKeys.
macOS:   double-tap of the Globe key (🌐) via GlobeTapListener.

Supports re-registration when the user changes the hotkey in settings.
"""
import logging
import sys
import threading
import time
from typing import Callable

from pynput import keyboard

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# macOS: Globe key double-tap listener
# ---------------------------------------------------------------------------

class GlobeTapListener:
    """
    Detects double-tap of the Globe key (🌐) on macOS and runs a callback.

    Uses suppress=False — all keys pass through the OS normally.
    Single-tap: Globe switches input source as usual (OS handles it).
    Double-tap (two presses within 350 ms): conversion callback is run.

    On double-tap the input source flips twice (cancels out) before conversion
    runs, so the layout ends up in the same state as before the double-tap.
    The conversion then switches to the correct layout as needed.

    Note: requires Accessibility permission so pynput can receive key events
    from other applications.

    PHASE 1: confirm _GLOBE_VK on your hardware with tools/detect_globe_key.py
    """

    _DOUBLE_TAP_MS = 350
    # Globe key virtual keycode on Apple keyboards — verify with detect_globe_key.py
    _GLOBE_VK = 63

    def __init__(self, callback: Callable[[], None]) -> None:
        self._callback = callback
        self._listener: keyboard.Listener | None = None
        self._lock = threading.Lock()
        self._last_tap: float = 0.0

    def start(self) -> None:
        with self._lock:
            self._stop_listener()
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                suppress=False,
            )
            self._listener.start()
            log.info('GlobeTapListener started (Globe vk=%d)', self._GLOBE_VK)

    def stop(self) -> None:
        with self._lock:
            self._stop_listener()

    def _stop_listener(self) -> None:
        if self._listener is None:
            return
        try:
            self._listener.stop()
            self._listener.join(timeout=2.0)
        except Exception:
            log.warning('GlobeTapListener stop error', exc_info=True)
        self._listener = None

    def _on_press(self, key) -> None:
        """Called for every key press. Only act on Globe key presses."""
        is_globe = hasattr(key, 'vk') and key.vk == self._GLOBE_VK
        if not is_globe:
            return

        now = time.monotonic()
        with self._lock:
            elapsed_ms = (now - self._last_tap) * 1000
            if elapsed_ms <= self._DOUBLE_TAP_MS and self._last_tap > 0:
                # Double-tap detected — run conversion
                self._last_tap = 0.0
                log.debug('Globe double-tap detected — running conversion')
                t = threading.Thread(target=self._callback, daemon=True, name='globe-callback')
                t.start()
            else:
                # First tap — record time, let Globe pass through naturally
                self._last_tap = now


# ---------------------------------------------------------------------------
# HotkeyListener — unified API for both platforms
# ---------------------------------------------------------------------------

class HotkeyListener:
    """
    Manages a single global hotkey that calls a callback when pressed.

    On Windows: uses pynput GlobalHotKeys with a keyboard shortcut string.
    On macOS:   uses GlobeTapListener (Globe double-tap); the hotkey string
                is accepted but ignored.

    Re-register by calling update_hotkey() which does stop+start atomically.
    """

    def __init__(self, hotkey: str, callback: Callable[[], None]) -> None:
        self._hotkey = hotkey
        self._callback = callback
        self._suspended = False
        self._lock = threading.Lock()

        if sys.platform == 'darwin':
            self._impl: GlobeTapListener | keyboard.GlobalHotKeys | None = (
                GlobeTapListener(callback=self._on_hotkey)
            )
        else:
            self._impl = None  # created in _start_listener

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start listening for the hotkey."""
        with self._lock:
            self._stop_impl()
            self._start_impl()

    def stop(self) -> None:
        """Stop listening."""
        with self._lock:
            self._stop_impl()

    def update_hotkey(self, new_hotkey: str) -> bool:
        """Atomically replace the current hotkey with a new one.

        On macOS this is a no-op (trigger is always Globe double-tap).
        Returns True on success, False if registration failed.
        """
        if sys.platform == 'darwin':
            self._hotkey = new_hotkey
            log.info('Hotkey string stored (macOS uses Globe key, not shortcut): %s', new_hotkey)
            return True

        with self._lock:
            old_hotkey = self._hotkey
            self._stop_impl()
            self._hotkey = new_hotkey
            if not self._suspended:
                try:
                    self._start_impl()
                except Exception:
                    log.warning(
                        'Failed to register hotkey %s, reverting to %s',
                        new_hotkey, old_hotkey, exc_info=True,
                    )
                    self._hotkey = old_hotkey
                    try:
                        self._start_impl()
                    except Exception:
                        log.error('Failed to restore previous hotkey %s', old_hotkey, exc_info=True)
                    return False
        log.info('Hotkey updated to: %s', new_hotkey)
        return True

    def suspend(self) -> None:
        """Temporarily disable the hotkey without forgetting it."""
        with self._lock:
            if not self._suspended:
                self._stop_impl()
                self._suspended = True
        log.info('Hotkey suspended')

    def resume(self) -> None:
        """Re-enable a suspended hotkey."""
        with self._lock:
            if self._suspended:
                self._suspended = False
                self._start_impl()
        log.info('Hotkey resumed')

    @property
    def is_suspended(self) -> bool:
        return self._suspended

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _start_impl(self) -> None:
        """Start the platform-appropriate listener (called under lock)."""
        if sys.platform == 'darwin':
            if self._impl is None:
                self._impl = GlobeTapListener(callback=self._on_hotkey)
            self._impl.start()
        else:
            pynput_hotkey = _to_pynput_hotkey(self._hotkey)
            self._impl = keyboard.GlobalHotKeys({pynput_hotkey: self._on_hotkey})
            self._impl.start()
            log.info('Hotkey listener started: %s → %s', self._hotkey, pynput_hotkey)

    def _stop_impl(self) -> None:
        """Stop the current listener (called under lock)."""
        if self._impl is None:
            return
        try:
            if sys.platform == 'darwin':
                self._impl.stop()
            else:
                self._impl.stop()
                self._impl.join(timeout=2.0)
        except Exception:
            log.warning('stop impl error', exc_info=True)
        if sys.platform != 'darwin':
            self._impl = None

    def _on_hotkey(self) -> None:
        """Called by the listener on trigger — dispatches callback in a worker thread."""
        if self._suspended:
            return
        log.debug('Hotkey triggered: %s', self._hotkey)
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
