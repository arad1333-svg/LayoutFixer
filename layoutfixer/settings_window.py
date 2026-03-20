"""
settings_window.py — customtkinter settings UI with three tabs:
  General | Key Map | Advanced
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

ACCENT = '#3b82f6'
BG_MAIN = '#1e1e2e'
BG_CARD = '#2a2a3e'
WIN_W, WIN_H = 500, 580


class SettingsWindow(ctk.CTkToplevel):
    """The settings window. Only one instance should exist at a time."""

    def __init__(self, listener=None, **kwargs):
        super().__init__(**kwargs)
        self._listener = listener
        self._settings = settings_manager.load()

        self.title('LayoutFixer Settings')
        self.geometry(f'{WIN_W}x{WIN_H}')
        self.resizable(False, False)
        self.configure(fg_color=BG_MAIN)

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
        self._tabview = ctk.CTkTabview(self, fg_color=BG_CARD, segmented_button_selected_color=ACCENT)
        self._tabview.pack(fill='both', expand=True, padx=16, pady=16)

        self._tabview.add('General')
        self._tabview.add('Key Map')
        self._tabview.add('Advanced')

        self._build_general_tab(self._tabview.tab('General'))
        self._build_keymap_tab(self._tabview.tab('Key Map'))
        self._build_advanced_tab(self._tabview.tab('Advanced'))

    # ------------------------------------------------------------------
    # Tab 1 — General
    # ------------------------------------------------------------------

    def _build_general_tab(self, parent):
        s = self._settings

        # Hotkey section
        ctk.CTkLabel(parent, text='HOTKEY', font=ctk.CTkFont(size=11, weight='bold'),
                     text_color='gray').pack(anchor='w', padx=16, pady=(20, 4))

        self._hotkey_var = tk.StringVar(value=s.get('hotkey', 'ctrl+alt+z'))
        for label, value in HOTKEY_OPTIONS:
            ctk.CTkRadioButton(
                parent, text=label, variable=self._hotkey_var, value=value,
                fg_color=ACCENT, border_color=ACCENT,
            ).pack(anchor='w', padx=24, pady=2)

        self._sep(parent)

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

        # Save button
        ctk.CTkButton(
            parent, text='Save', fg_color=ACCENT, hover_color='#2563eb',
            command=self._save,
        ).pack(pady=(8, 16))

    # ------------------------------------------------------------------
    # Tab 2 — Key Map
    # ------------------------------------------------------------------

    def _build_keymap_tab(self, parent):
        custom = self._settings.get('custom_keymap', {})
        effective = {**EN_TO_HE, **custom}

        ctk.CTkLabel(parent, text='Click a Hebrew cell and press a key to remap it.',
                     font=ctk.CTkFont(size=11), text_color='gray').pack(pady=(12, 4))

        # Scrollable frame for the table
        scroll_frame = ctk.CTkScrollableFrame(parent, fg_color=BG_CARD, height=360)
        scroll_frame.pack(fill='both', expand=True, padx=8, pady=4)

        # Header
        ctk.CTkLabel(scroll_frame, text='EN Key', font=ctk.CTkFont(weight='bold'), width=80).grid(
            row=0, column=0, padx=8, pady=4)
        ctk.CTkLabel(scroll_frame, text='HE Character', font=ctk.CTkFont(weight='bold'), width=120).grid(
            row=0, column=1, padx=8, pady=4)

        self._keymap_entries: list[tuple[str, ctk.CTkEntry]] = []

        for row_idx, (en_key, he_char) in enumerate(sorted(effective.items()), start=1):
            ctk.CTkLabel(scroll_frame, text=repr(en_key), width=80).grid(
                row=row_idx, column=0, padx=8, pady=2)

            entry = ctk.CTkEntry(scroll_frame, width=120, justify='center')
            entry.insert(0, he_char)
            entry.grid(row=row_idx, column=1, padx=8, pady=2)
            self._keymap_entries.append((en_key, entry))

        ctk.CTkButton(
            parent, text='Reset to Defaults', fg_color='gray30', hover_color='gray40',
            command=self._reset_keymap,
        ).pack(pady=8)

    def _reset_keymap(self):
        """Restore built-in map in the entry widgets."""
        for en_key, entry in self._keymap_entries:
            entry.delete(0, 'end')
            entry.insert(0, EN_TO_HE.get(en_key, ''))

    # ------------------------------------------------------------------
    # Tab 3 — Advanced
    # ------------------------------------------------------------------

    def _build_advanced_tab(self, parent):
        s = self._settings

        ctk.CTkLabel(parent, text='CLIPBOARD DELAY (ms)',
                     font=ctk.CTkFont(size=11, weight='bold'), text_color='gray').pack(
            anchor='w', padx=16, pady=(20, 2))

        self._delay_var = tk.IntVar(value=s.get('clipboard_delay_ms', 100))
        self._delay_label = ctk.CTkLabel(parent, text=f'{self._delay_var.get()} ms')
        self._delay_label.pack(anchor='e', padx=16)

        slider = ctk.CTkSlider(
            parent, from_=50, to=300, number_of_steps=25,
            variable=self._delay_var, button_color=ACCENT, progress_color=ACCENT,
            command=lambda v: self._delay_label.configure(text=f'{int(v)} ms'),
        )
        slider.pack(fill='x', padx=16)

        ctk.CTkLabel(parent, text='Increase if conversion misses text in slow apps.',
                     font=ctk.CTkFont(size=10), text_color='gray').pack(anchor='w', padx=16)

        self._sep(parent)

        self._debug_var = tk.BooleanVar(value=s.get('debug_log', False))
        self._toggle_row(parent, 'DEBUG LOGGING', self._debug_var,
                         subtitle='Writes verbose log to %APPDATA%\\LayoutFixer\\debug.log')

        self._sep(parent)

        ctk.CTkLabel(parent, text='LayoutFixer v1.0.0',
                     font=ctk.CTkFont(size=11), text_color='gray').pack(pady=(8, 2))

        ctk.CTkButton(
            parent, text='Reset All Settings', fg_color='#dc2626', hover_color='#b91c1c',
            command=self._reset_all,
        ).pack(pady=(4, 16))

    # ------------------------------------------------------------------
    # Save / Reset
    # ------------------------------------------------------------------

    def _save(self):
        s = self._settings

        # General tab
        old_hotkey = s.get('hotkey')
        s['hotkey'] = self._hotkey_var.get()
        s['auto_switch_layout'] = self._auto_switch_var.get()
        s['show_notifications'] = self._notifications_var.get()

        # Handle start-with-Windows toggle
        import autostart
        new_autostart = self._start_windows_var.get()
        if new_autostart != autostart.is_enabled():
            if new_autostart:
                autostart.enable()
            else:
                autostart.disable()
        s['start_with_windows'] = new_autostart

        # Key Map tab
        custom_keymap: dict[str, str] = {}
        for en_key, entry in self._keymap_entries:
            val = entry.get().strip()
            if val and val != EN_TO_HE.get(en_key, ''):
                custom_keymap[en_key] = val
        s['custom_keymap'] = custom_keymap

        # Advanced tab
        s['clipboard_delay_ms'] = int(self._delay_var.get())
        s['debug_log'] = self._debug_var.get()

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
        self.destroy()
        # Re-open fresh
        SettingsWindow(listener=self._listener)

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
        ctk.CTkFrame(parent, height=1, fg_color='gray30').pack(fill='x', padx=16, pady=8)

    def _toggle_row(self, parent, label: str, var: tk.BooleanVar, subtitle: str = ''):
        frame = ctk.CTkFrame(parent, fg_color='transparent')
        frame.pack(fill='x', padx=16, pady=4)

        text_frame = ctk.CTkFrame(frame, fg_color='transparent')
        text_frame.pack(side='left', fill='x', expand=True)

        ctk.CTkLabel(text_frame, text=label,
                     font=ctk.CTkFont(size=11, weight='bold')).pack(anchor='w')
        if subtitle:
            ctk.CTkLabel(text_frame, text=subtitle,
                         font=ctk.CTkFont(size=10), text_color='gray').pack(anchor='w')

        ctk.CTkSwitch(
            frame, text='', variable=var,
            onvalue=True, offvalue=False,
            button_color=ACCENT, progress_color=ACCENT,
        ).pack(side='right')


# ---------------------------------------------------------------------------
# Module-level singleton management
# ---------------------------------------------------------------------------

_window_instance: SettingsWindow | None = None
_window_lock = threading.Lock()


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
