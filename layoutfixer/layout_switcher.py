"""
layout_switcher.py — Switch the foreground window's keyboard layout via WinAPI.
"""
import ctypes
import logging

log = logging.getLogger(__name__)

LAYOUTS = {
    'en': '00000409',  # English (US)
    'he': '0000040D',  # Hebrew
}


def switch(direction: str) -> bool:
    """
    Switch the foreground window's keyboard layout.

    Args:
        direction: 'en_to_he' → switch to Hebrew layout.
                   'he_to_en' → switch to English layout.

    Returns:
        True on success, False on failure.
    """
    target_lang = 'he' if direction == 'en_to_he' else 'en'
    layout_id = LAYOUTS[target_lang]

    try:
        user32 = ctypes.windll.user32

        # Load (or retrieve cached) HKL for target layout
        hkl = user32.LoadKeyboardLayoutW(layout_id, 1)
        if not hkl:
            log.warning('LoadKeyboardLayoutW returned NULL for layout %s', layout_id)
            return False

        hwnd = user32.GetForegroundWindow()

        # Post WM_INPUTLANGCHANGEREQUEST to the foreground window
        WM_INPUTLANGCHANGEREQUEST = 0x0050
        user32.PostMessageW(hwnd, WM_INPUTLANGCHANGEREQUEST, 0, hkl)

        # Also activate at the thread level
        user32.ActivateKeyboardLayout(hkl, 0)

        log.debug('Switched layout to %s (%s)', target_lang, layout_id)
        return True

    except Exception:
        log.exception('Failed to switch keyboard layout')
        return False


def current_layout() -> str | None:
    """
    Return the LCID string of the foreground thread's current keyboard layout,
    or None on failure.
    """
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        thread_id = user32.GetWindowThreadProcessId(hwnd, None)
        hkl = user32.GetKeyboardLayout(thread_id)
        # Low word of HKL is the language identifier
        lang_id = hkl & 0xFFFF
        return f'{lang_id:08X}'
    except Exception:
        log.exception('Failed to get current keyboard layout')
        return None
