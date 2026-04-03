"""
converter.py — Hebrew ↔ English character map and conversion logic.

Maps physical QWERTY key positions to their Hebrew equivalents
(standard Israeli keyboard layout, as defined in Windows).
"""

# English key → Hebrew character (physical key position mapping)
EN_TO_HE: dict[str, str] = {
    'q': '/', 'w': "'", 'e': 'ק', 'r': 'ר', 't': 'א', 'y': 'ט',
    'u': 'ו', 'i': 'ן', 'o': 'ם', 'p': 'פ',
    'a': 'ש', 's': 'ד', 'd': 'ג', 'f': 'כ', 'g': 'ע', 'h': 'י',
    'j': 'ח', 'k': 'ל', 'l': 'ך', ';': 'ף',
    'z': 'ז', 'x': 'ס', 'c': 'ב', 'v': 'ה', 'b': 'נ', 'n': 'מ',
    'm': 'צ', ',': 'ת', '.': 'ץ', '/': '.', "'": ',',
    '[': ']', ']': '[',
}

# Hebrew character → English key (reverse map, auto-generated)
HE_TO_EN: dict[str, str] = {v: k for k, v in EN_TO_HE.items()}
assert len(HE_TO_EN) == len(EN_TO_HE), (
    f"HE_TO_EN collision: {len(EN_TO_HE) - len(HE_TO_EN)} duplicate(s)"
)


def _detect_direction(text: str) -> str:
    """
    Auto-detect whether text is Hebrew-typed-in-English-layout or vice versa.

    Counts Hebrew characters vs ASCII alpha characters.
    The majority language determines the direction.

    Returns 'en_to_he' if text is mostly English (user was in English layout),
    or 'he_to_en' if text is mostly Hebrew (user was in Hebrew layout).
    """
    he_count = sum(1 for ch in text if '\u05d0' <= ch <= '\u05ea')
    en_count = sum(1 for ch in text if ch.isascii() and ch.isalpha())

    # Default to en_to_he if equal or ambiguous
    return 'he_to_en' if he_count > en_count else 'en_to_he'


def convert(text: str, direction: str = 'auto', custom_keymap: dict[str, str] | None = None) -> str:
    """
    Convert text between Hebrew and English keyboard layouts.

    Args:
        text:          The text to convert.
        direction:     'auto', 'en_to_he', or 'he_to_en'.
                       'auto' detects from character majority.
        custom_keymap: Optional overrides for the built-in EN_TO_HE map.
                       Only keys present in the dict are overridden.

    Returns:
        Converted text. Unmapped characters (spaces, numbers, punctuation
        not in the map) are passed through unchanged.
    """
    if not text:
        return text

    # Build the effective keymap (apply custom overrides on top of built-in)
    en_to_he = dict(EN_TO_HE)
    if custom_keymap:
        en_to_he.update(custom_keymap)
    he_to_en = {v: k for k, v in en_to_he.items()}

    if direction == 'auto':
        direction = _detect_direction(text)

    if direction == 'en_to_he':
        mapping = en_to_he
        # Also handle uppercase: uppercase Latin maps to the same Hebrew letter
        result = []
        for ch in text:
            lower = ch.lower()
            if lower in mapping:
                result.append(mapping[lower])
            elif ch in mapping:
                result.append(mapping[ch])
            else:
                result.append(ch)
        return ''.join(result)

    elif direction == 'he_to_en':
        result = []
        for ch in text:
            result.append(he_to_en.get(ch, ch))
        return ''.join(result)

    else:
        raise ValueError(f"Unknown direction: {direction!r}. Use 'auto', 'en_to_he', or 'he_to_en'.")
