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

    # 3b. Materialize the start-at-login setting (ships ON by default): only
    # in the packaged app — a dev run would register the bare Python
    # interpreter as a login item.
    if getattr(sys, 'frozen', False) and settings.get('start_with_windows', True):
        try:
            import autostart
            if not autostart.is_enabled():
                autostart.enable()
                log.info('Start-at-login enabled (default)')
        except Exception:
            log.warning('Could not enable start-at-login', exc_info=True)

    # 4. Set customtkinter appearance
    import customtkinter as ctk
    theme = settings.get('theme', 'dark')
    if theme == 'system':
        theme = 'dark'   # legacy value — the System option was removed
    ctk.set_appearance_mode(theme)
    ctk.set_default_color_theme('blue')

    # 5. Hidden Tk root (required for settings window and tray notifications)
    import tkinter as tk
    import __main__
    __main__._tk_root = tk.Tk()
    __main__._tk_root.withdraw()

    # 5b. macOS: Tk switches the process to the Regular activation policy,
    # which puts a Dock icon up even though Info.plist has LSUIElement=true.
    # Set it back to Accessory so LayoutFixer stays menu-bar-only.
    if sys.platform == 'darwin':
        try:
            from AppKit import NSApplication
            NSApplicationActivationPolicyAccessory = 1
            NSApplication.sharedApplication().setActivationPolicy_(
                NSApplicationActivationPolicyAccessory)
        except Exception:
            log.warning('Could not set Accessory activation policy', exc_info=True)

    # 6. macOS: gate on Accessibility permission. The gate window polls until
    # the permission is granted, so the listener below starts with live
    # permission — no app restart needed. Returns False if the user quits.
    if sys.platform == 'darwin':
        from permission_gate import run_gate
        if not run_gate(__main__._tk_root):
            log.info('User quit at the permission gate')
            sys.exit(0)

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
            if sys.platform == 'darwin':
                tray_app._tray_icon.visible = False
            else:
                tray_app._tray_icon.stop()
        __main__._tk_root.quit()

    # 9. Start the system tray icon
    import tray_app

    if sys.platform == 'darwin':
        # macOS: tkinter's mainloop() (started below) drives the shared
        # NSApplication event loop, which also dispatches tray icon clicks —
        # so the icon is created on the main thread with no separate thread
        # or event loop of its own.
        tray_app.create_tray(listener, settings, on_open_settings, on_quit)
    else:
        # Windows: pystray runs its own blocking event loop on a background
        # thread.
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
