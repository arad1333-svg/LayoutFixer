"""
plat/autostart_mac.py — macOS LaunchAgent plist for start-at-login.

Fully implementable on Windows (pure Python, no pyobjc needed).
Only imported on sys.platform == 'darwin'.
"""
import logging
import plistlib
import sys
from pathlib import Path

log = logging.getLogger(__name__)

_PLIST_LABEL = 'com.layoutfixer.app'
_PLIST_PATH = Path.home() / 'Library' / 'LaunchAgents' / f'{_PLIST_LABEL}.plist'


def enable(exe_path: str | None = None) -> bool:
    """
    Write a LaunchAgent plist so LayoutFixer launches at login.

    Args:
        exe_path: Path to the .app bundle executable or Python script.
                  Defaults to the current process executable.

    Returns:
        True on success, False on failure.
    """
    path = exe_path or sys.executable
    plist_data = {
        'Label': _PLIST_LABEL,
        'ProgramArguments': [path],
        'RunAtLoad': True,
        'KeepAlive': False,
    }
    try:
        _PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_PLIST_PATH, 'wb') as f:
            plistlib.dump(plist_data, f)
        log.info('LaunchAgent written: %s', _PLIST_PATH)
        return True
    except OSError:
        log.exception('Failed to write LaunchAgent plist')
        return False


def disable() -> bool:
    """
    Remove the LaunchAgent plist.

    Returns:
        True on success (or already absent), False on error.
    """
    try:
        _PLIST_PATH.unlink(missing_ok=True)
        log.info('LaunchAgent removed: %s', _PLIST_PATH)
        return True
    except OSError:
        log.exception('Failed to remove LaunchAgent plist')
        return False


def is_enabled() -> bool:
    """Return True if the LaunchAgent plist exists."""
    return _PLIST_PATH.exists()
