"""
settings_manager.py - Load/save app settings to %APPDATA%/LayoutFixer/settings.json.
"""
import json
import os
from pathlib import Path

APP_NAME = 'LayoutFixer'

DEFAULTS: dict = {
    'hotkey': 'ctrl+alt+x',
    'auto_switch_layout': True,
    'start_with_windows': False,
    'show_notifications': True,
    'theme': 'system',
    'clipboard_delay_ms': 100,
    'debug_log': False,
    'custom_keymap': {},
}


def _settings_path() -> Path:
    appdata = os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')
    return Path(appdata) / APP_NAME / 'settings.json'


def load() -> dict:
    """Load settings from disk. Missing keys are filled with defaults."""
    path = _settings_path()
    settings = dict(DEFAULTS)
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                on_disk = json.load(f)
            settings.update(on_disk)
        except (json.JSONDecodeError, OSError):
            pass  # Corrupted file — use defaults
    return settings


def save(settings: dict) -> None:
    """Save settings to disk atomically, creating directories as needed."""
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def reset() -> dict:
    """Reset settings to defaults, save, and return them."""
    settings = dict(DEFAULTS)
    save(settings)
    return settings
