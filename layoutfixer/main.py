"""
main.py — Entry point for LayoutFixer.

Responsibilities:
  1. Single-instance mutex (prevent duplicate launches)
  2. Logging setup
  3. Start hotkey listener
  4. Start system tray (blocks until Exit is chosen)
"""
import ctypes
import logging
import os
import sys
import threading
from pathlib import Path


# ---------------------------------------------------------------------------
# Single-instance mutex
# ---------------------------------------------------------------------------

_MUTEX_NAME = 'LayoutFixer_SingleInstance_Mutex'
_mutex_handle = None


def _acquire_mutex() -> bool:
    """Return True if this is the first instance, False if already running."""
    global _mutex_handle
    _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    last_error = ctypes.windll.kernel32.GetLastError()
    ERROR_ALREADY_EXISTS = 183
    return last_error != ERROR_ALREADY_EXISTS


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_logging(debug: bool = False) -> None:
    appdata = os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')
    log_dir = Path(appdata) / 'LayoutFixer'
    log_dir.mkdir(parents=True, exist_ok=True)

    handlers: list[logging.Handler] = []

    if debug:
        log_path = log_dir / 'debug.log'
        fh = logging.FileHandler(log_path, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        handlers.append(fh)

    # Always log warnings/errors even without debug mode
    if not debug:
        err_path = log_dir / 'error.log'
        eh = logging.FileHandler(err_path, encoding='utf-8')
        eh.setLevel(logging.WARNING)
        handlers.append(eh)

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=handlers,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # 1. Single-instance check
    if not _acquire_mutex():
        ctypes.windll.user32.MessageBoxW(
            0,
            'LayoutFixer is already running.\nCheck the system tray.',
            'LayoutFixer',
            0x40,  # MB_ICONINFORMATION
        )
        sys.exit(0)

    # 2. Load settings
    import settings_manager
    settings = settings_manager.load()

    # 3. Logging
    _setup_logging(debug=settings.get('debug_log', False))
    log = logging.getLogger(__name__)
    log.info('LayoutFixer starting')

    # 4. Set customtkinter appearance
    import customtkinter as ctk
    theme = settings.get('theme', 'system')
    ctk.set_appearance_mode(theme)
    ctk.set_default_color_theme('blue')

    # 5. Hidden Tk root (required for settings window and tray notifications)
    import tkinter as tk
    import __main__
    __main__._tk_root = tk.Tk()
    __main__._tk_root.withdraw()

    # 6. Start hotkey listener
    from hotkey_listener import HotkeyListener
    from clipboard_handler import run_conversion

    hotkey = settings.get('hotkey', 'ctrl+alt+z')
    listener = HotkeyListener(hotkey=hotkey, callback=run_conversion)
    listener.start()
    log.info('Hotkey listener started: %s', hotkey)

    # 7. Define tray callbacks
    def on_open_settings():
        from settings_window import open_settings
        open_settings(listener=listener)

    def on_quit():
        log.info('LayoutFixer exiting')
        listener.stop()
        import tray_app
        if tray_app._tray_icon:
            tray_app._tray_icon.stop()
        __main__._tk_root.quit()

    # 8. Run tray in a background thread (it blocks until stopped)
    import tray_app

    tray_thread = threading.Thread(
        target=tray_app.run_tray,
        args=(listener, settings, on_open_settings, on_quit),
        daemon=True,
        name='tray',
    )
    tray_thread.start()

    # 9. Run Tk event loop on the main thread (required by tkinter)
    try:
        __main__._tk_root.mainloop()
    except KeyboardInterrupt:
        on_quit()


if __name__ == '__main__':
    main()
