"""
settings_window.py — customtkinter settings UI with three tabs:
  General | Hotkey | Key Map
"""
import logging
import sys
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

# Kinetic Terminal palette — (light-mode, dark-mode) pairs.
# customtkinter widgets accept these tuples directly and auto-switch with the
# appearance mode; plain tk widgets (Canvas/Frame/Label) can't, so they must
# resolve colors through _c() at render time and be re-rendered on theme change.
PRIMARY           = ('#3da81e', '#8eff71')
PRIMARY_HOVER     = ('#2f8c13', '#2ff801')
ON_PRIMARY        = ('#ffffff', '#064200')
SURFACE           = ('#f4f4f2', '#0e0e0e')
SURFACE_LOW       = ('#e9e9e6', '#131313')
SURFACE_CONTAINER = ('#fbfbfa', '#1a1919')
SURFACE_HIGH      = ('#e3e3e0', '#201f1f')
SURFACE_BRIGHT    = ('#d5d5d1', '#2c2c2c')
ON_SURFACE        = ('#171716', '#ffffff')
ON_SURFACE_VAR    = ('#5f5d5b', '#adaaaa')
OUTLINE           = ('#8f8d8a', '#777575')
OUTLINE_VAR       = ('#c6c4c1', '#494847')
ERROR             = ('#d84315', '#ff7351')
ERROR_HOVER       = ('#bf360c', '#e05a3a')


def _c(pair: tuple[str, str]) -> str:
    """Resolve a (light, dark) color pair against the current appearance mode."""
    return pair[0] if ctk.get_appearance_mode() == 'Light' else pair[1]

WIN_W, WIN_H = 500, 560


class AnimatedSwitch(tk.Canvas):
    """Animated pill-shaped toggle. Replaces ctk.CTkSwitch."""

    _TRACK_W = 52
    _TRACK_H = 22
    _KNOB_D  = 16
    _MARGIN  = 3
    _ANIM_MS = 180
    _TICK_MS = 16    # ~60 fps

    def __init__(self, parent, variable: tk.BooleanVar, **kwargs):
        super().__init__(
            parent,
            width=self._TRACK_W, height=self._TRACK_H,
            bd=0, highlightthickness=0,
            bg=_c(SURFACE_CONTAINER), cursor='hand2',
        )
        self._var     = variable
        self._anim_id = None
        self._knob_r  = self._KNOB_D // 2                            # 8
        self._x_off   = self._MARGIN + self._knob_r                  # 11
        self._x_on    = self._TRACK_W - self._MARGIN - self._knob_r  # 41
        self._knob_y  = self._TRACK_H // 2                           # 11

        self._current_knob_x = self._x_on if variable.get() else self._x_off
        self._render(self._current_knob_x)

        self.bind('<Button-1>', self._on_click)
        self._var.trace_add('write', self._on_var_changed)

    def _on_click(self, _event=None):
        self._var.set(not self._var.get())

    def _on_var_changed(self, *_):
        self._start_animation(self._var.get())

    def _start_animation(self, target_state: bool):
        import time
        if self._anim_id is not None:
            self.after_cancel(self._anim_id)
            self._anim_id = None
        self._anim_start_x  = self._current_knob_x
        self._anim_target_x = self._x_on if target_state else self._x_off
        self._anim_start_t  = time.perf_counter()
        self._tick()

    def _tick(self):
        import time
        elapsed = (time.perf_counter() - self._anim_start_t) * 1000
        t     = min(elapsed / self._ANIM_MS, 1.0)
        eased = t * t * (3.0 - 2.0 * t)    # smoothstep ease-in-out
        cx    = self._anim_start_x + eased * (self._anim_target_x - self._anim_start_x)
        self._render(cx)
        if t < 1.0:
            self._anim_id = self.after(self._TICK_MS, self._tick)
        else:
            self._anim_id = None

    def refresh_theme(self) -> None:
        """Re-resolve colors after an appearance-mode change."""
        self.configure(bg=_c(SURFACE_CONTAINER))
        self._render(self._current_knob_x)

    def _render(self, knob_cx: float):
        self._current_knob_x = knob_cx
        self.delete('all')
        state      = self._var.get()
        tw, th     = self._TRACK_W, self._TRACK_H
        r          = th // 2    # 11 — full pill
        track_fill = _c(PRIMARY)    if state else _c(SURFACE_HIGH)
        knob_fill  = _c(ON_PRIMARY) if state else _c(ON_SURFACE_VAR)
        self._pill(0, 0, tw, th, r, fill=track_fill, outline=_c(OUTLINE_VAR))
        kr = self._knob_r
        self.create_oval(
            knob_cx - kr, self._knob_y - kr,
            knob_cx + kr, self._knob_y + kr,
            fill=knob_fill, outline='',
        )

    def _pill(self, x1, y1, x2, y2, r, fill, outline):
        """Filled pill shape with a 1-px border.

        Built from two half-circle end caps + a center rectangle. Ovals have
        no straight edges, so there is no pieslice-edge seam through the
        track (a hairline used to show at the knob position).
        """
        fk = dict(fill=fill, outline=fill)
        self.create_oval(x1,       y1, x1 + 2*r, y2, **fk)
        self.create_oval(x2 - 2*r, y1, x2,       y2, **fk)
        self.create_rectangle(x1 + r, y1, x2 - r, y2, **fk)
        bk = dict(outline=outline, fill='')
        self.create_arc(x1,       y1, x1 + 2*r, y2, start=90,  extent=180, style='arc', **bk)
        self.create_arc(x2 - 2*r, y1, x2,       y2, start=270, extent=180, style='arc', **bk)
        self.create_line(x1 + r, y1, x2 - r, y1, fill=outline)
        self.create_line(x1 + r, y2, x2 - r, y2, fill=outline)


class LedRadioButton(tk.Canvas):
    """Canvas-based LED Dot radio button indicator (22×22 px)."""

    _SIZE      = 22
    _RING_W    = 3
    _DOT_D     = 8
    _FLASH_MS  = 80
    _SETTLE_MS = 180

    def __init__(self, parent, variable: tk.StringVar, value: str, **kwargs):
        super().__init__(
            parent,
            width=self._SIZE, height=self._SIZE,
            bd=0, highlightthickness=0,
            bg=_c(SURFACE_CONTAINER), cursor='hand2',
        )
        self._var       = variable
        self._value     = value
        self._hovering  = False
        self._flashing  = False
        self._flash_id  = None
        self._settle_id = None

        self._render()
        self.bind('<Button-1>', self._on_click)
        self._var.trace_add('write', self._on_var_changed)

    def set_hover(self, state: bool) -> None:
        self._hovering = state
        self._render()

    def _on_click(self, _event=None) -> None:
        if self._var.get() != self._value:
            self._var.set(self._value)

    def _on_var_changed(self, *_) -> None:
        if self._var.get() == self._value:
            self._start_flash()
        else:
            self._cancel_flash()
            self._render()

    def _start_flash(self) -> None:
        self._cancel_flash()
        self._flashing = True
        self._render()
        self._flash_id = self.after(self._FLASH_MS, self._end_flash_phase)

    def _end_flash_phase(self) -> None:
        self._flash_id = None
        self._flashing = False
        self._render()
        self._settle_id = self.after(self._SETTLE_MS - self._FLASH_MS, self._clear_settle)

    def _clear_settle(self) -> None:
        self._settle_id = None

    def _cancel_flash(self) -> None:
        if self._flash_id is not None:
            self.after_cancel(self._flash_id)
            self._flash_id = None
        if self._settle_id is not None:
            self.after_cancel(self._settle_id)
            self._settle_id = None
        self._flashing = False

    def refresh_theme(self) -> None:
        """Re-resolve colors after an appearance-mode change."""
        self.configure(bg=_c(SURFACE_CONTAINER))
        self._render()

    def _render(self) -> None:
        self.delete('all')
        selected = self._var.get() == self._value
        s, half  = self._SIZE, self._SIZE / 2
        rw       = self._RING_W

        ring_color = _c(
            (PRIMARY_HOVER if self._flashing else PRIMARY)
            if selected else
            (ON_SURFACE_VAR if self._hovering else OUTLINE_VAR)
        )

        self.create_oval(rw, rw, s - rw, s - rw, outline=ring_color, width=rw, fill='')

        if selected:
            r = self._DOT_D / 2
            self.create_oval(half - r, half - r, half + r, half + r,
                             fill=_c(ON_PRIMARY), outline='')


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
        # ── Tab bar ──────────────────────────────────────────────────
        tab_bar = ctk.CTkFrame(self, fg_color=SURFACE_LOW, corner_radius=0)
        tab_bar.pack(fill='x')

        # Bottom border beneath the tab bar
        ctk.CTkFrame(self, fg_color=OUTLINE_VAR, height=1, corner_radius=0).pack(fill='x')

        # Content area (fills remaining space)
        content_area = ctk.CTkFrame(self, fg_color=SURFACE_CONTAINER, corner_radius=0)
        content_area.pack(fill='both', expand=True)

        tab_names = ['General', 'Hotkey', 'Key Map']
        self._tab_frames: dict[str, ctk.CTkFrame] = {}
        self._tab_buttons: dict[str, ctk.CTkButton] = {}
        self._tab_indicators: dict[str, ctk.CTkFrame] = {}
        self._active_tab: str = ''

        # Build tab buttons with underline indicator
        for name in tab_names:
            group = ctk.CTkFrame(tab_bar, fg_color='transparent', corner_radius=0)
            group.pack(side='left')

            btn = ctk.CTkButton(
                group, text=name,
                fg_color='transparent',
                hover_color=SURFACE_HIGH,
                text_color=ON_SURFACE_VAR,
                font=ctk.CTkFont(family='Segoe UI', size=12, weight='bold'),
                corner_radius=0,
                height=38,
                width=90,
                command=lambda n=name: self._switch_tab(n),
            )
            btn.pack()

            indicator = ctk.CTkFrame(group, fg_color='transparent', height=2, corner_radius=0)
            indicator.pack(fill='x')

            self._tab_buttons[name] = btn
            self._tab_indicators[name] = indicator

        # Build content frames (one per tab)
        for name in tab_names:
            frame = ctk.CTkFrame(content_area, fg_color='transparent', corner_radius=0)
            self._tab_frames[name] = frame

        # Populate tab contents
        self._save_buttons: list[ctk.CTkButton] = []
        # Plain-tk widgets that must re-resolve colors on theme change
        self._theme_refreshers: list = []
        self._build_general_tab(self._tab_frames['General'])
        self._build_hotkey_tab(self._tab_frames['Hotkey'])
        self._build_keymap_tab(self._tab_frames['Key Map'])

        # Show first tab
        self._switch_tab('General')

        # Save-button UX: snapshot the just-loaded values, then watch every
        # input so the Save buttons only light up when something differs.
        self._saved_values = self._current_values()
        self._watch_inputs()
        self._refresh_save_buttons()

    def _switch_tab(self, name: str) -> None:
        """Activate a tab: update button/indicator styling and swap visible frame."""
        if self._active_tab:
            self._tab_frames[self._active_tab].pack_forget()
            self._tab_buttons[self._active_tab].configure(text_color=ON_SURFACE_VAR)
            self._tab_indicators[self._active_tab].configure(fg_color='transparent')

        self._active_tab = name
        self._tab_frames[name].pack(fill='both', expand=True)
        self._tab_buttons[name].configure(text_color=PRIMARY)
        self._tab_indicators[name].configure(fg_color=PRIMARY)

    # ------------------------------------------------------------------
    # Tab 1 — General
    # ------------------------------------------------------------------

    def _build_general_tab(self, parent):
        s = self._settings

        # Toggle: auto-switch layout
        self._auto_switch_var = tk.BooleanVar(value=s.get('auto_switch_layout', True))
        self._toggle_row(parent, 'AUTO-SWITCH LAYOUT', self._auto_switch_var,
                         subtitle='After converting, switch keyboard language to match.')

        # Toggle: start at login (label differs by platform)
        self._start_windows_var = tk.BooleanVar(value=s.get('start_with_windows', False))
        login_label = 'START AT LOGIN' if sys.platform == 'darwin' else 'START WITH WINDOWS'
        self._toggle_row(parent, login_label, self._start_windows_var)

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
        # Normalise stored value; 'system' is a legacy value from before the
        # System option was removed — treat it as Dark (the brand default)
        _theme_map = {'dark': 'Dark', 'light': 'Light'}
        display_theme = _theme_map.get(theme_val.lower(), 'Dark')
        self._theme_var = tk.StringVar(value=display_theme)

        def _on_theme_change(value):
            ctk.set_appearance_mode(value.lower())
            for refresh in self._theme_refreshers:
                refresh()

        ctk.CTkOptionMenu(
            parent,
            values=['Dark', 'Light'],
            variable=self._theme_var,
            command=_on_theme_change,
            fg_color=SURFACE_HIGH,
            button_color=SURFACE_BRIGHT,
            button_hover_color=OUTLINE,
            text_color=ON_SURFACE,
        ).pack(anchor='w', padx=16, pady=(0, 8))

        self._sep(parent)

        # Save button
        self._add_save_button(parent)

    # ------------------------------------------------------------------
    # Tab 2 — Hotkey
    # ------------------------------------------------------------------

    def _build_hotkey_tab(self, parent):
        s = self._settings

        ctk.CTkLabel(
            parent, text='ACTIVATION HOTKEY',
            font=ctk.CTkFont(family='Segoe UI', size=11, weight='bold'),
            text_color=ON_SURFACE_VAR,
        ).pack(anchor='w', padx=16, pady=(20, 4))

        if sys.platform == 'darwin':
            # macOS: trigger is always Globe double-tap — no user choice needed
            ctk.CTkLabel(
                parent,
                text='Double-tap Globe (\U0001f310) to convert',
                font=ctk.CTkFont(family='Segoe UI', size=13),
                text_color=ON_SURFACE,
            ).pack(anchor='w', padx=24, pady=(8, 16))
            self._hotkey_var = tk.StringVar(
                value=s.get('hotkey', settings_manager.DEFAULTS['hotkey'])
            )
        else:
            self._hotkey_var = tk.StringVar(
                value=s.get('hotkey', settings_manager.DEFAULTS['hotkey'])
            )
            for label, value in HOTKEY_OPTIONS:
                row = tk.Frame(parent, bg=_c(SURFACE_CONTAINER), cursor='hand2')
                row.pack(anchor='w', padx=24, pady=4)

                led = LedRadioButton(row, variable=self._hotkey_var, value=value)
                led.pack(side='left')

                lbl = tk.Label(row, text=label, bg=_c(SURFACE_CONTAINER), fg=_c(ON_SURFACE),
                               font=('Segoe UI', 12), cursor='hand2')
                lbl.pack(side='left', padx=(8, 0))

                def _refresh_row(row=row, lbl=lbl, led=led):
                    row.configure(bg=_c(SURFACE_CONTAINER))
                    lbl.configure(bg=_c(SURFACE_CONTAINER), fg=_c(ON_SURFACE))
                    led.refresh_theme()
                self._theme_refreshers.append(_refresh_row)

                lbl.bind('<Button-1>', led._on_click)
                row.bind('<Button-1>', led._on_click)
                for widget in (row, led, lbl):
                    widget.bind('<Enter>', lambda _e, l=led: l.set_hover(True))
                    widget.bind('<Leave>', lambda _e, l=led: l.set_hover(False))

        self._sep(parent)

        self._add_save_button(parent)

    # ------------------------------------------------------------------
    # Tab 3 — Key Map
    # ------------------------------------------------------------------

    def _build_keymap_tab(self, parent):
        custom = self._settings.get('custom_keymap', {})
        effective = {**EN_TO_HE, **custom}

        ctk.CTkLabel(
            parent, text='Click a cell and type a new character to remap.',
            font=ctk.CTkFont(family='Segoe UI', size=11),
            text_color=ON_SURFACE_VAR,
        ).pack(pady=(12, 4))

        # Scrollable frame for the table
        scroll_frame = ctk.CTkScrollableFrame(parent, fg_color=SURFACE_CONTAINER, height=320)
        scroll_frame.pack(fill='both', expand=True, padx=8, pady=4)

        # Sticky header row
        header = ctk.CTkFrame(scroll_frame, fg_color=SURFACE_HIGH, corner_radius=0)
        header.pack(fill='x')
        ctk.CTkLabel(
            header, text='EN KEY', width=80,
            font=ctk.CTkFont(family='Segoe UI', size=10, weight='bold'),
            text_color=ON_SURFACE_VAR,
        ).pack(side='left', padx=16, pady=8)
        ctk.CTkLabel(
            header, text='HE CHAR',
            font=ctk.CTkFont(family='Segoe UI', size=10, weight='bold'),
            text_color=ON_SURFACE_VAR,
        ).pack(side='right', padx=16, pady=8)

        self._keymap_entries: list[tuple[str, ctk.CTkEntry]] = []

        for row_idx, (en_key, he_char) in enumerate(sorted(effective.items()), start=1):
            row_bg = SURFACE_LOW if row_idx % 2 == 1 else SURFACE_CONTAINER
            row_frame = ctk.CTkFrame(scroll_frame, fg_color=row_bg, corner_radius=0)
            row_frame.pack(fill='x')

            ctk.CTkLabel(
                row_frame, text=en_key, width=80,
                font=ctk.CTkFont(family='Segoe UI', size=12),
                text_color=ON_SURFACE_VAR,
            ).pack(side='left', padx=16, pady=5)

            entry = ctk.CTkEntry(
                row_frame, width=80, justify='center',
                fg_color='transparent',
                border_color=OUTLINE_VAR,
                border_width=1,
                text_color=ON_SURFACE,
            )
            entry.insert(0, he_char)
            entry.pack(side='right', padx=16, pady=5)
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
        # delete/insert don't fire <KeyRelease>, so refresh explicitly
        self._refresh_save_buttons()

    # ------------------------------------------------------------------
    # Unsaved-change tracking (Save button UX)
    # ------------------------------------------------------------------

    def _current_values(self) -> dict:
        """Snapshot of every user-editable input, for unsaved-change detection."""
        return {
            'auto_switch': self._auto_switch_var.get(),
            'start_windows': self._start_windows_var.get(),
            'notifications': self._notifications_var.get(),
            'theme': self._theme_var.get(),
            'hotkey': self._hotkey_var.get(),
            'keymap': tuple(entry.get() for _key, entry in self._keymap_entries),
        }

    def _is_dirty(self) -> bool:
        return self._current_values() != self._saved_values

    def _watch_inputs(self) -> None:
        for var in (self._auto_switch_var, self._start_windows_var,
                    self._notifications_var, self._theme_var, self._hotkey_var):
            var.trace_add('write', self._on_input_changed)
        for _key, entry in self._keymap_entries:
            entry.bind('<KeyRelease>', self._on_input_changed)

    def _on_input_changed(self, *_) -> None:
        self._refresh_save_buttons()

    def _refresh_save_buttons(self) -> None:
        if self._is_dirty():
            for btn in self._save_buttons:
                btn.configure(fg_color=PRIMARY, hover_color=PRIMARY_HOVER,
                              text_color=ON_PRIMARY)
        else:
            for btn in self._save_buttons:
                btn.configure(fg_color=SURFACE_HIGH, hover_color=SURFACE_HIGH,
                              text_color=ON_SURFACE_VAR)

    def _mark_saved(self) -> None:
        self._saved_values = self._current_values()
        self._refresh_save_buttons()

    # ------------------------------------------------------------------
    # Save / Reset
    # ------------------------------------------------------------------

    def _save(self):
        if not self._is_dirty():
            return  # nothing to save — inactive button is a no-op

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
                self._mark_saved()
                self._show_error('Could not register that hotkey — your previous hotkey has been restored.')
                return

        # Window stays open; buttons grey out until the next change
        self._mark_saved()

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

    def _add_save_button(self, parent) -> None:
        btn = ctk.CTkButton(
            parent, text='Save',
            fg_color=PRIMARY, hover_color=PRIMARY_HOVER, text_color=ON_PRIMARY,
            font=ctk.CTkFont(family='Segoe UI', size=13, weight='bold'),
            command=self._save,
        )
        btn.pack(pady=(8, 16))
        self._save_buttons.append(btn)

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
            text_color=ON_SURFACE,
        ).pack(anchor='w')
        if subtitle:
            ctk.CTkLabel(
                text_frame, text=subtitle,
                font=ctk.CTkFont(family='Segoe UI', size=12),
                text_color=ON_SURFACE_VAR,
            ).pack(anchor='w')

        switch = AnimatedSwitch(frame, variable=var)
        switch.pack(side='right', pady=1)
        self._theme_refreshers.append(switch.refresh_theme)


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
