"""
plat/ — Platform abstraction layer for LayoutFixer.

Detects sys.platform and re-exports the correct implementations under
a single unified API. All consumers import from here — never directly
from plat.clipboard_win, plat.system_mac, etc.
"""
import sys

if sys.platform == 'darwin':
    from .clipboard_mac import (
        save_clipboard,
        restore_clipboard,
        get_clipboard_counter,
        wait_for_clipboard_change,
        release_hotkey_modifiers,
        send_copy,
        send_paste,
    )
    from .layout_mac import switch as switch_layout, current_layout
    from .autostart_mac import (
        enable as autostart_enable,
        disable as autostart_disable,
        is_enabled as autostart_is_enabled,
    )
    from .system_mac import (
        acquire_mutex,
        show_already_running_dialog,
        get_log_dir,
        get_settings_dir,
        check_accessibility_permission,
    )

elif sys.platform == 'win32':
    from .clipboard_win import (
        save_clipboard,
        restore_clipboard,
        get_clipboard_counter,
        wait_for_clipboard_change,
        release_hotkey_modifiers,
        send_copy,
        send_paste,
    )
    from .layout_win import switch as switch_layout, current_layout
    from .autostart_win import (
        enable as autostart_enable,
        disable as autostart_disable,
        is_enabled as autostart_is_enabled,
    )
    from .system_win import (
        acquire_mutex,
        show_already_running_dialog,
        get_log_dir,
        get_settings_dir,
    )

else:
    raise ImportError(f'LayoutFixer does not support platform: {sys.platform}')
