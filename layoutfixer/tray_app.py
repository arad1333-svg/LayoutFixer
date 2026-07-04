"""
tray_app.py — System tray icon and context menu using pystray.
"""
import logging
import queue
import sys
import threading
from pathlib import Path

from PIL import Image
import pystray

log = logging.getLogger(__name__)

# Module-level reference so show_notification() can reach the icon
_tray_icon: pystray.Icon | None = None

# ---------------------------------------------------------------------------
# macOS safe-call queue
#
# On macOS, pystray NSMenuItem callbacks are delivered via NSApplication's
# ObjC event dispatch, which re-acquires the Python GIL through pyobjc's
# PyGILState_Ensure(). This bypasses tkinter's own PyEval_SaveThread /
# PyEval_RestoreThread pair, leaving tkinter's internal saved-tstate as NULL.
# Any subsequent root.after() callback that calls PythonCmd →
# PyEval_RestoreThread(NULL) crashes the process.
#
# Even calling root.after(0, fn) from within the NSMenuItem callback is
# enough to trigger this — it is a Tcl call and touches the corrupted state.
#
# Solution: NSMenuItem callbacks only call _callback_queue.put(fn), which is
# a pure Python operation (no Tcl). A recurring root.after(50, ...) poll loop,
# started before mainloop() in the correct Tcl context, drains the queue and
# calls fn() safely.
# ---------------------------------------------------------------------------
_callback_queue: queue.SimpleQueue = queue.SimpleQueue()


def _tk_schedule(fn) -> None:
    """Post fn to the macOS-safe callback queue (no Tcl calls)."""
    _callback_queue.put(fn)


def _start_callback_poller(root) -> None:
    """Start the recurring poll loop that drains _callback_queue safely.

    Must be called from the Tk main thread before mainloop() (macOS only).
    The loop reschedules itself every 50 ms for the lifetime of the app.
    """
    def _poll():
        try:
            while True:
                fn = _callback_queue.get_nowait()
                try:
                    fn()
                except Exception:
                    log.debug('Error in deferred tray callback', exc_info=True)
        except queue.Empty:
            pass
        root.after(50, _poll)
    root.after(50, _poll)


# ---------------------------------------------------------------------------
# Icon image helpers
# ---------------------------------------------------------------------------

def _load_icon(suspended: bool = False) -> Image.Image:
    """Load the tray icon image. Falls back to a generated placeholder if missing."""
    assets = Path(__file__).parent / 'assets'
    icon_path = assets / 'icon.png'

    if icon_path.exists():
        img = Image.open(icon_path).convert('RGBA')
    else:
        img = _generate_icon()

    if suspended:
        # Greyscale the icon to indicate suspended state
        img = img.convert('LA').convert('RGBA')

    return img


def _generate_icon() -> Image.Image:
    """Generate a simple placeholder icon when no asset file is present."""
    from PIL import ImageDraw, ImageFont

    size = 64
    img = Image.new('RGBA', (size, size), (30, 30, 46, 255))  # dark background
    draw = ImageDraw.Draw(img)

    # Blue rounded rectangle
    margin = 4
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=10,
        fill=(59, 130, 246, 255),  # blue accent
    )

    # "LF" text
    try:
        font = ImageFont.truetype('segoeui.ttf', 22)
    except OSError:
        font = ImageFont.load_default()

    draw.text((size // 2, size // 2), 'LF', fill='white', font=font, anchor='mm')
    return img


# ---------------------------------------------------------------------------
# Tray menu builder
# ---------------------------------------------------------------------------

def _build_menu(listener, settings: dict, on_settings: callable, on_quit: callable):
    """Build the pystray menu. Rebuilt on every toggle to reflect current state."""

    def toggle_suspend(icon, item):
        if listener.is_suspended:
            listener.resume()
        else:
            listener.suspend()
        # Rebuild icon and menu to reflect new state
        icon.icon = _load_icon(suspended=listener.is_suspended)
        icon.menu = _build_menu(listener, settings, on_settings, on_quit)

    def toggle_autostart(icon, item):
        import autostart
        if autostart.is_enabled():
            autostart.disable()
            settings['start_with_windows'] = False
        else:
            autostart.enable()
            settings['start_with_windows'] = True
        import settings_manager
        settings_manager.save(settings)
        icon.menu = _build_menu(listener, settings, on_settings, on_quit)

    import autostart
    status_label = 'Active (click to Suspend)' if not listener.is_suspended else 'Suspended (click to Resume)'
    autostart_label = 'Start at Login' if sys.platform == 'darwin' else 'Start with Windows'

    return pystray.Menu(
        pystray.MenuItem('Open Settings', lambda icon, item: _tk_schedule(on_settings)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(status_label, toggle_suspend),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            autostart_label,
            toggle_autostart,
            checked=lambda item: autostart.is_enabled(),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('About LayoutFixer', _show_about),
        pystray.MenuItem('Exit', lambda icon, item: _tk_schedule(on_quit)),
    )


def _show_about(icon, item):
    def _show():
        import tkinter.messagebox as mb
        mb.showinfo('LayoutFixer', 'LayoutFixer v1.0.0\nHebrew ↔ English layout converter.')
    _tk_schedule(_show)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def show_notification(message: str) -> None:
    """Show a system notification.

    Windows: pystray tray balloon. macOS: pystray has no notification
    support, so use osascript's `display notification` instead.
    """
    if sys.platform == 'darwin':
        try:
            import subprocess
            safe = message.replace('\\', '\\\\').replace('"', '\\"')
            subprocess.Popen([
                'osascript', '-e',
                f'display notification "{safe}" with title "LayoutFixer"',
            ])
        except Exception:
            log.debug('Failed to show macOS notification', exc_info=True)
        return

    global _tray_icon
    if _tray_icon is not None:
        try:
            _tray_icon.notify(message, 'LayoutFixer')
        except Exception:
            log.debug('Failed to show tray notification', exc_info=True)


def _create_icon(listener, settings: dict, on_settings: callable, on_quit: callable) -> pystray.Icon:
    """Build the pystray Icon and start the welcome-notification timer."""
    global _tray_icon

    icon_image = _load_icon(suspended=listener.is_suspended)
    menu = _build_menu(listener, settings, on_settings, on_quit)

    _tray_icon = pystray.Icon(
        name='LayoutFixer',
        icon=icon_image,
        title='LayoutFixer',
        menu=menu,
    )

    # Show a "running" notification shortly after startup (platform-specific
    # trigger wording), unless the user disabled notifications
    def _welcome():
        import time
        time.sleep(1.5)
        if not settings.get('show_notifications', True):
            return
        if sys.platform == 'darwin':
            show_notification('LayoutFixer is running in the menu bar. '
                              'Select gibberish text and double-tap the Globe key to fix it.')
        else:
            show_notification('LayoutFixer is running. Select text and press the hotkey to convert it.')

    threading.Thread(target=_welcome, daemon=True).start()

    return _tray_icon


def run_tray(listener, settings: dict, on_settings: callable, on_quit: callable) -> None:
    """
    Create and run the system tray icon. This call blocks until the icon is stopped.
    Call on a dedicated thread (Windows).
    """
    icon = _create_icon(listener, settings, on_settings, on_quit)
    icon.run()


def create_tray(listener, settings: dict, on_settings: callable, on_quit: callable) -> None:
    """
    Create the tray icon and mark it ready/visible without starting pystray's
    own event loop (macOS). Call on the main thread, before tkinter's
    mainloop() starts — mainloop() drives the shared NSApplication event loop
    that dispatches tray icon clicks.

    Also starts the macOS safe-call poller so that menu callbacks (which cannot
    touch Tcl directly) can defer work to the Tk event loop via _callback_queue.
    """
    import __main__
    icon = _create_icon(listener, settings, on_settings, on_quit)
    icon._mark_ready()
    icon.visible = True
    if hasattr(__main__, '_tk_root'):
        _start_callback_poller(__main__._tk_root)
