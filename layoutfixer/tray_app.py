"""
tray_app.py — System tray icon and context menu using pystray.
"""
import logging
import threading
from pathlib import Path

from PIL import Image
import pystray

log = logging.getLogger(__name__)

# Module-level reference so show_notification() can reach the icon
_tray_icon: pystray.Icon | None = None


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

    return pystray.Menu(
        pystray.MenuItem('Open Settings', lambda icon, item: on_settings()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(status_label, toggle_suspend),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            'Start with Windows',
            toggle_autostart,
            checked=lambda item: autostart.is_enabled(),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('About LayoutFixer', _show_about),
        pystray.MenuItem('Exit', lambda icon, item: on_quit()),
    )


def _show_about(icon, item):
    import __main__

    def _show():
        import tkinter.messagebox as mb
        mb.showinfo('LayoutFixer', 'LayoutFixer v1.0.0\nHebrew ↔ English layout converter.')

    if hasattr(__main__, '_tk_root'):
        __main__._tk_root.after(0, _show)
    else:
        _show()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def show_notification(message: str) -> None:
    """Show a Windows tray balloon notification."""
    global _tray_icon
    if _tray_icon is not None:
        try:
            _tray_icon.notify(message, 'LayoutFixer')
        except Exception:
            log.debug('Failed to show tray notification', exc_info=True)


def run_tray(listener, settings: dict, on_settings: callable, on_quit: callable) -> None:
    """
    Create and run the system tray icon. This call blocks until the icon is stopped.
    Call on the main thread or a dedicated thread.
    """
    global _tray_icon

    icon_image = _load_icon(suspended=listener.is_suspended)
    menu = _build_menu(listener, settings, on_settings, on_quit)

    _tray_icon = pystray.Icon(
        name='LayoutFixer',
        icon=icon_image,
        title='LayoutFixer',
        menu=menu,
    )

    # Show first-run notification in a brief delay
    def _welcome():
        import time
        time.sleep(1.5)
        show_notification('LayoutFixer is running. Select text and press the hotkey to convert it.')

    threading.Thread(target=_welcome, daemon=True).start()

    _tray_icon.run()
