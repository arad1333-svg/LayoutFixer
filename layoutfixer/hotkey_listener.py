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

    Single-tap behaviour: after the double-tap window expires (350 ms) the
    Globe press is re-injected via Quartz so macOS still switches the input
    source normally.

    Double-tap behaviour: both presses are suppressed and the conversion
    callback is run instead.

    Note: requires Accessibility permission (pynput suppress=True).
    """

    _DOUBLE_TAP_MS = 350
    # Globe key virtual keycode on Apple keyboards.
    # Confirmed value on most Apple keyboards — verify on Phase 1 hardware.
    _GLOBE_VK = 63

    def __init__(self, callback: Callable[[], None]) -> None:
        self._callback = callback
        self._listener: keyboard.Listener | None = None
        self._lock = threading.Lock()
        self._last_tap: float = 0.0
        self._pending_reinject: threading.Timer | None = None

    def start(self) -> None:
        with self._lock:
            self._stop_listener()
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                suppress=True,
            )
            self._listener.start()
            log.info('GlobeTapListener started (Globe vk=%d)', self._GLOBE_VK)

    def stop(self) -> None:
        with self._lock:
            self._stop_listener()
            if self._pending_reinject:
                self._pending_reinject.cancel()
                self._pending_reinject = None

    def _stop_listener(self) -> None:
        if self._listener is None:
            return
        try:
            self._listener.stop()
            self._listener.join(timeout=2.0)
        except Exception:
            log.warning('GlobeTapListener stop error', exc_info=True)
        self._listener = None

    def _on_press(self, key) -> bool | None:
        """Called for every key press. Return False from suppress=True listener
        to suppress the event; None / True to pass it through.

        Because suppress=True suppresses ALL keys, we must re-inject
        non-Globe keys manually.
        """
        # Check if this is the Globe key
        is_globe = (
            hasattr(key, 'vk') and key.vk == self._GLOBE_VK
        )

        if not is_globe:
            # Re-inject non-Globe key so the rest of the OS sees it
            self._reinject_key(key)
            return None  # allow (suppress=True means we need explicit pass-through)

        now = time.monotonic()
        with self._lock:
            elapsed_ms = (now - self._last_tap) * 1000
            if elapsed_ms <= self._DOUBLE_TAP_MS and self._last_tap > 0:
                # Double-tap detected — cancel pending reinject, run conversion
                if self._pending_reinject:
                    self._pending_reinject.cancel()
                    self._pending_reinject = None
                self._last_tap = 0.0
                log.debug('Globe double-tap detected — running conversion')
                t = threading.Thread(target=self._callback, daemon=True, name='globe-callback')
                t.start()
            else:
                # First tap — schedule re-injection after timeout
                self._last_tap = now
                if self._pending_reinject:
                    self._pending_reinject.cancel()
                delay = self._DOUBLE_TAP_MS / 1000
                self._pending_reinject = threading.Timer(delay, self._do_reinject_globe)
                self._pending_reinject.daemon = True
                self._pending_reinject.start()

        return None  # suppress (listener already has suppress=True)

    def _do_reinject_globe(self) -> None:
        """Re-inject the Globe key so macOS switches the input source."""
        with self._lock:
            self._pending_reinject = None
            self._last_tap = 0.0
        self._reinject_globe()

    def _reinject_globe(self) -> None:
        """Post a Globe key-down + key-up via Quartz CGEventPost."""
        try:
            import Quartz  # type: ignore[import]
            ev_down = Quartz.CGEventCreateKeyboardEvent(None, self._GLOBE_VK, True)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev_down)
            ev_up = Quartz.CGEventCreateKeyboardEvent(None, self._GLOBE_VK, False)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev_up)
        except Exception:
            log.exception('Globe key re-injection failed')

    def _reinject_key(self, key) -> None:
        """Re-inject a non-Globe key via Quartz (because suppress=True ate it)."""
        try:
            import Quartz  # type: ignore[import]
            vk = getattr(key, 'vk', None)
            if vk is None:
                return
            ev_down = Quartz.CGEventCreateKeyboardEvent(None, vk, True)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev_down)
            ev_up = Quartz.CGEventCreateKeyboardEvent(None, vk, False)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev_up)
        except Exception:
            log.debug('Key re-injection failed for %r', key, exc_info=True)


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
