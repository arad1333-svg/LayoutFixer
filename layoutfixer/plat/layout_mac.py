"""
plat/layout_mac.py — Switch macOS input source (keyboard layout).

Uses Carbon TIS API via ctypes (no subprocess). Falls back to AppleScript only if
the ctypes path fails.
Only imported on sys.platform == 'darwin'.

All TIS* calls are marshalled to the main thread: macOS 26 kills the process
(SIGTRAP, dispatch_assert_queue) when they run on any other thread.
"""
import ctypes
import logging
import subprocess
import threading

log = logging.getLogger(__name__)

# AppleScript input source names — confirmed on hardware in Phase 1
_LANG_NAMES = {
    'he': 'Hebrew',
    'en': 'ABC',
}

# Cached ctypes handles — loaded once on first call to _load_frameworks()
_carbon = None
_cf = None


def _load_frameworks():
    global _carbon, _cf
    if _carbon is not None:
        return

    _carbon = ctypes.CDLL('/System/Library/Frameworks/Carbon.framework/Carbon')
    _cf = ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')

    _carbon.TISCreateInputSourceList.restype = ctypes.c_void_p
    _carbon.TISCreateInputSourceList.argtypes = [ctypes.c_void_p, ctypes.c_bool]
    _carbon.TISGetInputSourceProperty.restype = ctypes.c_void_p
    _carbon.TISGetInputSourceProperty.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    _carbon.TISSelectInputSource.restype = ctypes.c_int32
    _carbon.TISSelectInputSource.argtypes = [ctypes.c_void_p]
    _carbon.TISCopyCurrentKeyboardInputSource.restype = ctypes.c_void_p
    _carbon.TISCopyCurrentKeyboardInputSource.argtypes = []

    _cf.CFArrayGetCount.restype = ctypes.c_long
    _cf.CFArrayGetCount.argtypes = [ctypes.c_void_p]
    _cf.CFArrayGetValueAtIndex.restype = ctypes.c_void_p
    _cf.CFArrayGetValueAtIndex.argtypes = [ctypes.c_void_p, ctypes.c_long]
    _cf.CFStringGetCString.restype = ctypes.c_bool
    _cf.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
    _cf.CFRelease.restype = None
    _cf.CFRelease.argtypes = [ctypes.c_void_p]


def _run_on_main_thread(func, timeout: float = 3.0):
    """Run func() on the Tk main thread and return its result.

    Uses tray_app's callback queue (drained every 50 ms by the Tk event
    loop). Falls back to a direct call when already on the main thread or
    when the app's Tk root isn't running (unit tests, CLI usage).
    """
    if threading.current_thread() is threading.main_thread():
        return func()

    import __main__
    if getattr(__main__, '_tk_root', None) is None:
        return func()

    import tray_app
    done = threading.Event()
    result = {}

    def _call():
        try:
            result['value'] = func()
        except Exception as exc:
            result['error'] = exc
        finally:
            done.set()

    tray_app._tk_schedule(_call)
    if not done.wait(timeout):
        raise TimeoutError('main-thread TIS call timed out')
    if 'error' in result:
        raise result['error']
    return result['value']


def switch(direction: str) -> bool:
    """
    Switch the active input source.

    Args:
        direction: 'en_to_he' → switch to Hebrew.
                   'he_to_en' → switch to English.

    Returns:
        True on success, False on failure.
    """
    target_lang = 'he' if direction == 'en_to_he' else 'en'

    if _switch_via_carbon(target_lang):
        return True

    return _switch_via_applescript(target_lang)


def _switch_via_carbon(target_lang: str) -> bool:
    """Use Carbon TIS API via ctypes to activate the target language."""
    try:
        return _run_on_main_thread(lambda: _switch_via_carbon_impl(target_lang))
    except Exception:
        log.debug('Carbon ctypes switch failed', exc_info=True)
        return False


def _switch_via_carbon_impl(target_lang: str) -> bool:
    """The actual TIS calls — must only run on the main thread."""
    try:
        _load_frameworks()

        prop_langs = ctypes.c_void_p.in_dll(_carbon, 'kTISPropertyInputSourceLanguages').value
        if prop_langs is None:
            return False

        target = 'he' if target_lang == 'he' else 'en'
        kCFStringEncodingUTF8 = 0x08000100

        sources = _carbon.TISCreateInputSourceList(None, False)
        if not sources:
            return False
        try:
            count = _cf.CFArrayGetCount(sources)
            for i in range(count):
                source = _cf.CFArrayGetValueAtIndex(sources, i)
                if not source:
                    continue
                langs = _carbon.TISGetInputSourceProperty(source, prop_langs)
                if not langs:
                    continue
                for j in range(_cf.CFArrayGetCount(langs)):
                    lang_str = _cf.CFArrayGetValueAtIndex(langs, j)
                    if not lang_str:
                        continue
                    buf = ctypes.create_string_buffer(16)
                    if _cf.CFStringGetCString(lang_str, buf, 16, kCFStringEncodingUTF8):
                        if buf.value.decode() == target:
                            return _carbon.TISSelectInputSource(source) == 0
        finally:
            _cf.CFRelease(sources)
        return False
    except Exception:
        log.debug('Carbon ctypes switch failed', exc_info=True)
        return False


def _switch_via_applescript(target_lang: str) -> bool:
    """Click the named input source via AppleScript (fallback)."""
    name = _LANG_NAMES.get(target_lang, target_lang)
    script = (
        f'tell application "System Events"\n'
        f'    tell process "TextInputMenuAgent"\n'
        f'        tell menu bar item 1 of menu bar 2\n'
        f'            click\n'
        f'            click menu item "{name}" of menu 1\n'
        f'        end tell\n'
        f'    end tell\n'
        f'end tell'
    )
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            log.debug('Switched input source to %s via AppleScript', target_lang)
            return True
        log.warning('AppleScript switch failed: %s', result.stderr.strip())
        return False
    except Exception:
        log.exception('AppleScript switch error')
        return False


def current_layout() -> str | None:
    """
    Return a language string for the current input source ('en', 'he', etc.),
    or None on failure.
    """
    try:
        return _run_on_main_thread(_current_layout_impl)
    except Exception:
        log.debug('current_layout failed', exc_info=True)
        return None


def _current_layout_impl() -> str | None:
    """The actual TIS calls — must only run on the main thread."""
    try:
        _load_frameworks()

        prop_langs = ctypes.c_void_p.in_dll(_carbon, 'kTISPropertyInputSourceLanguages').value
        if prop_langs is None:
            return None

        kCFStringEncodingUTF8 = 0x08000100
        source = _carbon.TISCopyCurrentKeyboardInputSource()
        if not source:
            return None
        try:
            langs = _carbon.TISGetInputSourceProperty(source, prop_langs)
            if not langs or _cf.CFArrayGetCount(langs) == 0:
                return None
            lang_str = _cf.CFArrayGetValueAtIndex(langs, 0)
            if not lang_str:
                return None
            buf = ctypes.create_string_buffer(16)
            if _cf.CFStringGetCString(lang_str, buf, 16, kCFStringEncodingUTF8):
                return buf.value.decode()
            return None
        finally:
            _cf.CFRelease(source)
    except Exception:
        log.debug('current_layout failed', exc_info=True)
        return None
