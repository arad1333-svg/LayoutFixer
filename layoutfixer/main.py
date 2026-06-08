"""
main.py — Entry point for LayoutFixer.

Responsibilities:
  1. Single-instance mutex (prevent duplicate launches)
  2. Logging setup
  3. Start hotkey listener
  4. Start system tray (blocks until Exit is chosen)
"""
import logging
import sys
import threading
from pathlib import Path

from plat import acquire_mutex, show_already_running_dialog, get_log_dir


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_logging(debug: bool = False) -> None:
    log_dir = get_log_dir()
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
    if not acquire_mutex():
        show_already_running_dialog()
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

    # 6. macOS: check Accessibility permission (hotkeys won't work without it)
    if sys.platform == 'darwin':
        from plat import check_accessibility_permission
        import tkinter.messagebox
        if not check_accessibility_permission():
            tkinter.messagebox.showwarning(
                'LayoutFixer — Permission Required',
                'LayoutFixer needs Accessibility access to work.\n\n'
                '1. Open System Settings > Privacy & Security > Accessibility\n'
                '2. Enable LayoutFixer\n'
                '3. Restart LayoutFixer\n\n'
                'Hotkeys will NOT work until permission is granted.',
            )

    # 7. Start hotkey listener
    from hotkey_listener import HotkeyListener
    from clipboard_handler import run_conversion

    hotkey = settings.get('hotkey', 'ctrl+alt+z')
    listener = HotkeyListener(hotkey=hotkey, callback=run_conversion)
    listener.start()
    log.info('Hotkey listener started: %s', hotkey)

    # 8. Define tray callbacks
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

    # 9. Run tray in a background thread (it blocks until stopped)
    import tray_app

    tray_thread = threading.Thread(
        target=tray_app.run_tray,
        args=(listener, settings, on_open_settings, on_quit),
        daemon=True,
        name='tray',
    )
    tray_thread.start()

    # 10. Run Tk event loop on the main thread (required by tkinter)
    try:
        __main__._tk_root.mainloop()
    except KeyboardInterrupt:
        on_quit()


if __name__ == '__main__':
    main()
