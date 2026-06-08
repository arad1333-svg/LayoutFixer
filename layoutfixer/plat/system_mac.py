"""
plat/system_mac.py — macOS single-instance lock, dialog, path helpers, and
Accessibility permission check.

Only imported on sys.platform == 'darwin'.
"""
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_APP_SUPPORT = Path.home() / 'Library' / 'Application Support' / 'LayoutFixer'
_LOG_BASE = Path.home() / 'Library' / 'Logs' / 'LayoutFixer'
_LOCK_FILE = _APP_SUPPORT / '.lock'

# Keep the lock fd open for the lifetime of the process (releasing it would
# free the lock). None means not yet acquired.
_lock_fd = None


def acquire_mutex() -> bool:
    """
    Acquire an exclusive file lock on ~/.../LayoutFixer/.lock.

    Returns:
        True if this is the first instance (lock acquired).
        False if LayoutFixer is already running (lock already held).
    """
    global _lock_fd
    import fcntl
    _APP_SUPPORT.mkdir(parents=True, exist_ok=True)
    try:
        _lock_fd = open(_LOCK_FILE, 'w')
        fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False
    except Exception:
        log.exception('acquire_mutex failed')
        return False


def show_already_running_dialog() -> None:
    """Show a tkinter info dialog informing the user the app is already running."""
    import tkinter as tk
    import tkinter.messagebox as mb
    root = tk.Tk()
    root.withdraw()
    mb.showinfo('LayoutFixer', 'LayoutFixer is already running.\nCheck the menu bar.')
    root.destroy()


def get_settings_dir() -> Path:
    """Return ~/Library/Application Support/LayoutFixer"""
    return _APP_SUPPORT


def get_log_dir() -> Path:
    """Return ~/Library/Logs/LayoutFixer"""
    return _LOG_BASE


def check_accessibility_permission() -> bool:
    """
    Check whether Accessibility permission has been granted.

    Prompts the user via the system dialog if not yet granted (the
    AXTrustedCheckOptionPrompt flag opens System Settings automatically).

    Returns:
        True if permission is already granted, False otherwise.
    """
    try:
        from ApplicationServices import (  # type: ignore[import]
            AXIsProcessTrustedWithOptions,
            kAXTrustedCheckOptionPrompt,
        )
        options = {kAXTrustedCheckOptionPrompt: True}
        return bool(AXIsProcessTrustedWithOptions(options))
    except Exception:
        log.warning('check_accessibility_permission: ApplicationServices unavailable')
        return False
