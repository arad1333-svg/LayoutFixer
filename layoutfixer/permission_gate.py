"""
permission_gate.py — macOS first-run Accessibility gate.

One window that guides the user to grant Accessibility access and polls
until it is granted. Startup continues only after the grant, so the
keyboard listener is created with live permission — no app restart needed.

Only used on sys.platform == 'darwin'.
"""
import logging
import subprocess

import customtkinter as ctk

from settings_window import (
    PRIMARY, PRIMARY_HOVER, ON_PRIMARY,
    SURFACE, SURFACE_HIGH, SURFACE_BRIGHT,
    ON_SURFACE, ON_SURFACE_VAR, OUTLINE_VAR,
)

log = logging.getLogger(__name__)

_POLL_MS = 1500

_ACCESSIBILITY_PANE = (
    'x-apple.systempreferences:com.apple.preference.security'
    '?Privacy_Accessibility'
)


def _is_trusted() -> bool:
    """Silently check Accessibility permission (no system prompt)."""
    try:
        from ApplicationServices import AXIsProcessTrusted  # type: ignore[import]
        return bool(AXIsProcessTrusted())
    except Exception:
        log.warning('AXIsProcessTrusted unavailable', exc_info=True)
        return False


def _open_settings_pane() -> None:
    try:
        subprocess.Popen(['open', _ACCESSIBILITY_PANE])
    except Exception:
        log.warning('Could not open System Settings', exc_info=True)


def run_gate(root) -> bool:
    """Block until Accessibility is granted or the user quits.

    Returns True when permission is granted, False if the user chose Quit.
    """
    if _is_trusted():
        return True

    # Registers LayoutFixer in the Accessibility list on a fresh machine
    # (and shows the standard macOS dialog — its button works too).
    from plat import check_accessibility_permission
    check_accessibility_permission()

    result = {'granted': False}

    win = ctk.CTkToplevel(root)
    win.title('LayoutFixer')
    win.resizable(False, False)
    win.configure(fg_color=SURFACE)
    # Stay on top so the instructions remain visible next to System Settings
    win.attributes('-topmost', True)

    body = ctk.CTkFrame(win, fg_color='transparent')
    body.pack(fill='both', expand=True, padx=40, pady=(32, 28))

    ctk.CTkLabel(
        body, text='PERMISSION NEEDED',
        font=ctk.CTkFont(family='Segoe UI', size=12, weight='bold'),
        text_color=PRIMARY,
    ).pack(pady=(0, 10))

    ctk.CTkLabel(
        body,
        text='LayoutFixer needs Accessibility access\n'
             'to detect the Globe (\U0001f310) double-tap.',
        font=ctk.CTkFont(family='Segoe UI', size=14),
        text_color=ON_SURFACE, justify='center',
    ).pack(pady=(0, 20))

    steps = ctk.CTkFrame(
        body, fg_color=SURFACE_HIGH, corner_radius=10,
        border_width=1, border_color=OUTLINE_VAR,
    )
    steps.pack(fill='x', pady=(0, 20))
    ctk.CTkLabel(
        steps,
        text='1.  Click "Open System Settings"\n'
             '2.  Toggle LayoutFixer ON\n'
             '     (already ON?  toggle it OFF, then ON)',
        font=ctk.CTkFont(family='Segoe UI', size=12),
        text_color=ON_SURFACE_VAR, justify='left',
    ).pack(anchor='w', padx=18, pady=14)

    ctk.CTkButton(
        body, text='Open System Settings',
        fg_color=PRIMARY, hover_color=PRIMARY_HOVER, text_color=ON_PRIMARY,
        font=ctk.CTkFont(family='Segoe UI', size=13, weight='bold'),
        height=40, command=_open_settings_pane,
    ).pack(fill='x', pady=(0, 18))

    status = ctk.CTkLabel(
        body, text='●  Waiting for permission…',
        font=ctk.CTkFont(family='Segoe UI', size=12),
        text_color=ON_SURFACE_VAR,
    )
    status.pack(pady=(0, 16))

    def _quit():
        result['granted'] = False
        win.destroy()

    ctk.CTkButton(
        body, text='Quit LayoutFixer',
        fg_color='transparent', hover_color=SURFACE_HIGH,
        text_color=ON_SURFACE_VAR, border_width=1, border_color=OUTLINE_VAR,
        font=ctk.CTkFont(family='Segoe UI', size=11),
        command=_quit, height=28, width=140,
    ).pack()

    win.protocol('WM_DELETE_WINDOW', _quit)

    def _poll():
        if not win.winfo_exists():
            return
        if _is_trusted():
            result['granted'] = True
            status.configure(text='✓  Permission granted!', text_color=PRIMARY)
            win.after(900, win.destroy)
        else:
            win.after(_POLL_MS, _poll)

    # Center on screen
    win.update_idletasks()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 3
    win.geometry(f'+{x}+{y}')
    win.lift()
    win.focus_force()

    win.after(_POLL_MS, _poll)
    root.wait_window(win)
    return result['granted']
