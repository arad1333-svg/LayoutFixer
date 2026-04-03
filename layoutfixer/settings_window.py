"""
settings_window.py — customtkinter settings UI with three tabs:
  General | Hotkey | Key Map
"""
import logging
import threading
import tkinter as tk

import customtkinter as ctk

from converter import EN_TO_HE
import settings_manager

log = logging.getLogger(__name__)

# Hotkey preset options
HOTKEY_OPTIONS = [
    ('Ctrl + Alt + X  (recommended)', 'ctrl+alt+x'),
    ('Ctrl + Alt + Z', 'ctrl+alt+z'),
    ('Ctrl + Alt + F', 'ctrl+alt+f'),
]

# Kinetic Terminal palette
PRIMARY           = '#8eff71'
PRIMARY_HOVER     = '#2ff801'
ON_PRIMARY        = '#064200'
SURFACE           = '#0e0e0e'
SURFACE_LOW       = '#131313'
SURFACE_CONTAINER = '#1a1919'
SURFACE_HIGH      = '#201f1f'
SURFACE_BRIGHT    = '#2c2c2c'
ON_SURFACE        = '#ffffff'
ON_SURFACE_VAR    = '#adaaaa'
OUTLINE           = '#777575'
OUTLINE_VAR       = '#494847'
ERROR             = '#ff7351'
ERROR_HOVER       = '#e05a3a'

WIN_W, WIN_H = 500, 560


class SettingsWindow(ctk.CTkToplevel):
    """The settings window. Only one instance should exist at a time."""

    def __init__(self, listener=None, **kwargs):
        super().__init__(**kwargs)
        self._listener = listener
        self._settings = settings_manager.load()

        self.title('LayoutFixer Settings')
        self.geometry(f'{WIN_W}x{WIN_H}')
        self.resizable(False, False)
        self.configure(fg_color=SURFACE)

        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() - WIN_W) // 2
        y = (self.winfo_screenheight() - WIN_H) // 2
        self.geometry(f'+{x}+{y}')

        # Keep on top briefly so it surfaces on open
        self.lift()
        self.focus_force()

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self._tabview = ctk.CTkTabview(
            self,
            fg_color=SURFACE_CONTAINER,
            segmented_button_selected_color=PRIMARY,
            segmented_button_unselected_color=SURFACE_LOW,
            segmented_button_selected_hover_color=PRIMARY_HOVER,
            segmented_button_unselected_hover_color=SURFACE_HIGH,
        )
        self._tabview.pack(fill='both', expand=True, padx=16, pady=16)

        self._tabview.add('General')
        self._tabview.add('Hotkey')
        self._tabview.add('Key Map')

        self._build_general_tab(self._tabview.tab('General'))
        self._build_hotkey_tab(self._tabview.tab('Hotkey'))
        self._build_keymap_tab(self._tabview.tab('Key Map'))

    # ------------------------------------------------------------------
    # Tab 1 — General
    # ------------------------------------------------------------------

    def _build_general_tab(self, parent):
        s = self._settings

        # Toggle: auto-switch layout
        self._auto_switch_var = tk.BooleanVar(value=s.get('auto_switch_layout', True))
        self._toggle_row(parent, 'AUTO-SWITCH LAYOUT', self._auto_switch_var,
                         subtitle='After converting, switch keyboard language to match.')

        # Toggle: start with Windows
        self._start_windows_var = tk.BooleanVar(value=s.get('start_with_windows', False))
        self._toggle_row(parent, 'START WITH WINDOWS', self._start_windows_var)

        # Toggle: show notifications
        self._notifications_var = tk.BooleanVar(value=s.get('show_notifications', True))
        self._toggle_row(parent, 'SHOW NOTIFICATIONS', self._notifications_var)

        self._sep(parent)

        # Theme option
        ctk.CTkLabel(
            parent, text='THEME',
            font=ctk.CTkFont(family='Segoe UI', size=11, weight='bold'),
            text_color=ON_SURFACE_VAR,
        ).pack(anchor='w', padx=16, pady=(8, 2))

        theme_val = s.get('theme', settings_manager.DEFAULTS['theme'])
        # Normalise stored value to match OptionMenu display values
        _theme_map = {'system': 'System', 'dark': 'Dark', 'light': 'Light'}
        display_theme = _theme_map.get(theme_val.lower(), 'System')
        self._theme_var = tk.StringVar(value=display_theme)

        def _on_theme_change(value):
            ctk.set_appearance_mode(value.lower())

        ctk.CTkOptionMenu(
            parent,
            values=['System', 'Dark', 'Light'],
            variable=self._theme_var,
            command=_on_theme_change,
            fg_color=SURFACE_HIGH,
            button_color=SURFACE_BRIGHT,
            button_hover_color=OUTLINE,
            text_color=ON_SURFACE,
        ).pack(anchor='w', padx=16, pady=(0, 8))

        self._sep(parent)

        # Save button
        ctk.CTkButton(
            parent, text='Save',
            fg_color=PRIMARY, hover_color=PRIMARY_HOVER, text_color=ON_PRIMARY,
            font=ctk.CTkFont(family='Segoe UI', size=13, weight='bold'),
            command=self._save,
        ).pack(pady=(8, 16))

    # ------------------------------------------------------------------
    # Tab 2 — Hotkey
    # ------------------------------------------------------------------

    def _build_hotkey_tab(self, parent):
        s = self._settings

        ctk.CTkLabel(
            parent, text='HOTKEY',
            font=ctk.CTkFont(family='Segoe UI', size=11, weight='bold'),
            text_color=ON_SURFACE_VAR,
        ).pack(anchor='w', padx=16, pady=(20, 4))

        self._hotkey_var = tk.StringVar(
            value=s.get('hotkey', settings_manager.DEFAULTS['hotkey'])
        )
        for label, value in HOTKEY_OPTIONS:
            ctk.CTkRadioButton(
                parent, text=label, variable=self._hotkey_var, value=value,
                fg_color=PRIMARY, border_color=OUTLINE_VAR, hover_color=PRIMARY_HOVER,
                font=ctk.CTkFont(family='Segoe UI', size=12),
            ).pack(anchor='w', padx=24, pady=2)

        self._sep(parent)

        ctk.CTkButton(
            parent, text='Save',
            fg_color=PRIMARY, hover_color=PRIMARY_HOVER, text_color=ON_PRIMARY,
            font=ctk.CTkFont(family='Segoe UI', size=13, weight='bold'),
            command=self._save,
        ).pack(pady=(8, 16))

    # ------------------------------------------------------------------
    # Tab 3 — Key Map
    # ------------------------------------------------------------------

    def _build_keymap_tab(self, parent):
        custom = self._settings.get('custom_keymap', {})
        effective = {**EN_TO_HE, **custom}

        ctk.CTkLabel(
            parent, text='Click a Hebrew cell and press a key to remap it.',
            font=ctk.CTkFont(family='Segoe UI', size=11),
            text_color=ON_SURFACE_VAR,
        ).pack(pady=(12, 4))

        # Scrollable frame for the table
        scroll_frame = ctk.CTkScrollableFrame(parent, fg_color=SURFACE_CONTAINER, height=360)
        scroll_frame.pack(fill='both', expand=True, padx=8, pady=4)

        # Header
        ctk.CTkLabel(
            scroll_frame, text='EN Key',
            font=ctk.CTkFont(family='Segoe UI', weight='bold'), width=80,
        ).grid(row=0, column=0, padx=8, pady=4)
        ctk.CTkLabel(
            scroll_frame, text='HE Character',
            font=ctk.CTkFont(family='Segoe UI', weight='bold'), width=120,
        ).grid(row=0, column=1, padx=8, pady=4)

        self._keymap_entries: list[tuple[str, ctk.CTkEntry]] = []

        for row_idx, (en_key, he_char) in enumerate(sorted(effective.items()), start=1):
            ctk.CTkLabel(scroll_frame, text=repr(en_key), width=80).grid(
                row=row_idx, column=0, padx=8, pady=2)

            entry = ctk.CTkEntry(scroll_frame, width=120, justify='center')
            entry.insert(0, he_char)
            entry.grid(row=row_idx, column=1, padx=8, pady=2)
            self._keymap_entries.append((en_key, entry))

        ctk.CTkButton(
            parent, text='Reset to Defaults',
            fg_color=SURFACE_HIGH, hover_color=SURFACE_BRIGHT,
            text_color=ON_SURFACE_VAR, border_width=1, border_color=OUTLINE_VAR,
            font=ctk.CTkFont(family='Segoe UI', size=12),
            command=self._reset_keymap,
        ).pack(pady=8)

    def _reset_keymap(self):
        """Restore built-in map in the entry widgets."""
        for en_key, entry in self._keymap_entries:
            entry.delete(0, 'end')
            entry.insert(0, EN_TO_HE.get(en_key, ''))

    # ------------------------------------------------------------------
    # Save / Reset
    # ------------------------------------------------------------------

    def _save(self):
        s = self._settings

        # General tab
        s['auto_switch_layout'] = self._auto_switch_var.get()
        s['show_notifications'] = self._notifications_var.get()
        s['theme'] = self._theme_var.get().lower()

        # Handle start-with-Windows toggle
        import autostart
        new_autostart = self._start_windows_var.get()
        if new_autostart != autostart.is_enabled():
            if new_autostart:
                autostart.enable()
            else:
                autostart.disable()
        s['start_with_windows'] = new_autostart

        # Hotkey tab
        old_hotkey = s.get('hotkey')
        s['hotkey'] = self._hotkey_var.get()

        # Key Map tab
        custom_keymap: dict[str, str] = {}
        for en_key, entry in self._keymap_entries:
            val = entry.get().strip()
            if val and val != EN_TO_HE.get(en_key, ''):
                custom_keymap[en_key] = val
        s['custom_keymap'] = custom_keymap

        settings_manager.save(s)

        # Re-register hotkey if changed
        if self._listener and s['hotkey'] != old_hotkey:
            success = self._listener.update_hotkey(s['hotkey'])
            if not success:
                # Revert to old hotkey and re-save
                s['hotkey'] = old_hotkey
                settings_manager.save(s)
                self._hotkey_var.set(old_hotkey)
                self._show_error('Could not register that hotkey — your previous hotkey has been restored.')
                return

        self.destroy()

    def _reset_all(self):
        self._settings = settings_manager.reset()
        listener = self._listener
        self.destroy()
        open_settings(listener=listener)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _show_error(self, message: str) -> None:
        """Show a temporary error banner at the top of the window."""
        banner = ctk.CTkLabel(
            self, text=message,
            fg_color='#7f1d1d', text_color='#fca5a5',
            corner_radius=6, font=ctk.CTkFont(size=11),
        )
        banner.place(relx=0.5, rely=0.97, anchor='s', relwidth=0.95)
        self.after(4000, banner.destroy)

    def _sep(self, parent):
        ctk.CTkFrame(parent, height=1, fg_color=OUTLINE_VAR).pack(fill='x', padx=16, pady=8)

    def _toggle_row(self, parent, label: str, var: tk.BooleanVar, subtitle: str = ''):
        frame = ctk.CTkFrame(parent, fg_color='transparent')
        frame.pack(fill='x', padx=16, pady=4)

        text_frame = ctk.CTkFrame(frame, fg_color='transparent')
        text_frame.pack(side='left', fill='x', expand=True)

        ctk.CTkLabel(
            text_frame, text=label,
            font=ctk.CTkFont(family='Segoe UI', size=11, weight='bold'),
        ).pack(anchor='w')
        if subtitle:
            ctk.CTkLabel(
                text_frame, text=subtitle,
                font=ctk.CTkFont(family='Segoe UI', size=10),
                text_color=ON_SURFACE_VAR,
            ).pack(anchor='w')

        ctk.CTkSwitch(
            frame, text='', variable=var,
            onvalue=True, offvalue=False,
            button_color=PRIMARY, progress_color=PRIMARY,
            button_hover_color=PRIMARY_HOVER, fg_color=OUTLINE_VAR,
        ).pack(side='right')


# ---------------------------------------------------------------------------
# Module-level singleton management
# ---------------------------------------------------------------------------

_window_instance: SettingsWindow | None = None
_window_lock = threading.RLock()


def open_settings(listener=None) -> None:
    """Open the settings window, or bring the existing one to front."""
    global _window_instance

    def _open():
        global _window_instance
        with _window_lock:
            if _window_instance is not None and _window_instance.winfo_exists():
                _window_instance.lift()
                _window_instance.focus_force()
                return
            _window_instance = SettingsWindow(listener=listener)

    # Must run on the main thread (Tk requires it)
    try:
        import __main__
        if hasattr(__main__, '_tk_root'):
            __main__._tk_root.after(0, _open)
        else:
            _open()
    except Exception:
        _open()
