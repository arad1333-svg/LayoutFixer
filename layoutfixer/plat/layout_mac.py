"""
plat/layout_mac.py — Switch macOS input source (keyboard layout).

Phase 1: implement via Carbon TISSelectInputSource / AppleScript.
Only imported on sys.platform == 'darwin'.
"""
import logging
import subprocess

log = logging.getLogger(__name__)

# AppleScript input source names (may vary — Phase 1 confirms on hardware)
_LANG_NAMES = {
    'he': 'Hebrew',
    'en': 'U.S.',
}


def switch(direction: str) -> bool:
    """
    Switch the active input source.

    Args:
        direction: 'en_to_he' → switch to Hebrew.
                   'he_to_en' → switch to English (U.S.).

    Returns:
        True on success, False on failure.
    """
    target_lang = 'he' if direction == 'en_to_he' else 'en'

    # Try Carbon first (more reliable, doesn't depend on menu item name)
    if _switch_via_carbon(target_lang):
        return True

    # Fallback: AppleScript click on input menu
    return _switch_via_applescript(target_lang)


def _switch_via_carbon(target_lang: str) -> bool:
    """Use Carbon TISSelectInputSource to activate the target language."""
    try:
        from Carbon import HIToolbox  # type: ignore[import]

        language_code = 'he' if target_lang == 'he' else 'en'
        # Filter input sources by language
        props = {HIToolbox.kTISPropertyInputSourceLanguages: [language_code]}
        sources = HIToolbox.TISCreateInputSourceList(props, False)
        if sources and HIToolbox.CFArrayGetCount(sources) > 0:
            source = HIToolbox.CFArrayGetValueAtIndex(sources, 0)
            HIToolbox.TISSelectInputSource(source)
            log.debug('Switched input source to %s via Carbon', target_lang)
            return True
        log.warning('No Carbon input source found for language: %s', target_lang)
        return False
    except Exception:
        log.debug('Carbon switch failed', exc_info=True)
        return False


def _switch_via_applescript(target_lang: str) -> bool:
    """Click the named input source via AppleScript (fallback)."""
    name = _LANG_NAMES.get(target_lang, target_lang)
    script = (
        f'tell application "System Events"\n'
        f'    tell process "SystemUIServer"\n'
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
        from Carbon import HIToolbox  # type: ignore[import]
        source = HIToolbox.TISCopyCurrentKeyboardInputSource()
        langs = HIToolbox.TISGetInputSourceProperty(
            source, HIToolbox.kTISPropertyInputSourceLanguages
        )
        if langs and len(langs) > 0:
            return langs[0]
        return None
    except Exception:
        log.debug('current_layout failed', exc_info=True)
        return None
