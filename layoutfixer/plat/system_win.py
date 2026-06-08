"""
plat/system_win.py — Windows single-instance mutex, dialog, and path helpers.

Extracted from main.py. Only imported on sys.platform == 'win32'.
"""
import ctypes
import logging
import os
import sys
from pathlib import Path

log = logging.getLogger(__name__)

_MUTEX_NAME = 'LayoutFixer_SingleInstance_Mutex'
_mutex_handle = None


def acquire_mutex() -> bool:
    """
    Create a named Windows mutex.

    Returns:
        True if this is the first instance (mutex acquired).
        False if LayoutFixer is already running (ERROR_ALREADY_EXISTS).
    """
    global _mutex_handle
    _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    ERROR_ALREADY_EXISTS = 183
    return ctypes.windll.kernel32.GetLastError() != ERROR_ALREADY_EXISTS


def show_already_running_dialog() -> None:
    """Show a Windows MessageBox informing the user the app is already running."""
    ctypes.windll.user32.MessageBoxW(
        0,
        'LayoutFixer is already running.\nCheck the system tray.',
        'LayoutFixer',
        0x40,  # MB_ICONINFORMATION
    )


def get_settings_dir() -> Path:
    """Return the settings directory: %APPDATA%\\LayoutFixer"""
    appdata = os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')
    return Path(appdata) / 'LayoutFixer'


def get_log_dir() -> Path:
    """Return the log directory: %APPDATA%\\LayoutFixer (same as settings dir)."""
    return get_settings_dir()
