"""
autostart.py — Manage the Windows Registry Run key for start-with-Windows.
"""
import logging
import sys

log = logging.getLogger(__name__)

APP_NAME = 'LayoutFixer'
RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'


def _get_winreg():
    try:
        import winreg
        return winreg
    except ImportError:
        return None


def enable(exe_path: str | None = None) -> bool:
    """
    Add LayoutFixer to the Windows startup registry key.

    Args:
        exe_path: Path to the executable. Defaults to the current process executable.

    Returns:
        True on success, False on failure.
    """
    winreg = _get_winreg()
    if not winreg:
        log.warning('winreg not available — not on Windows?')
        return False

    path = exe_path or sys.executable
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{path}"')
        log.info('Added %s to startup registry', APP_NAME)
        return True
    except OSError:
        log.exception('Failed to add startup registry entry')
        return False


def disable() -> bool:
    """
    Remove LayoutFixer from the Windows startup registry key.

    Returns:
        True on success (or already absent), False on error.
    """
    winreg = _get_winreg()
    if not winreg:
        return False

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, APP_NAME)
        log.info('Removed %s from startup registry', APP_NAME)
        return True
    except FileNotFoundError:
        return True  # Already absent — that's fine
    except OSError:
        log.exception('Failed to remove startup registry entry')
        return False


def is_enabled() -> bool:
    """Return True if the startup registry entry exists."""
    winreg = _get_winreg()
    if not winreg:
        return False

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_NAME)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        log.exception('Failed to check startup registry entry')
        return False
