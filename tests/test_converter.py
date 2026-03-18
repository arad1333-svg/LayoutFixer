"""
Unit tests for converter.py.

Run with: pytest tests/test_converter.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'layoutfixer'))

import pytest
from converter import convert, EN_TO_HE, HE_TO_EN, _detect_direction


class TestCharacterMap:
    def test_en_to_he_has_all_keys(self):
        expected_en_keys = set('qwertyuiopasdfghjkl;zxcvbnm,./\'[]')
        assert set(EN_TO_HE.keys()) == expected_en_keys

    def test_he_to_en_is_reverse_of_en_to_he(self):
        for en, he in EN_TO_HE.items():
            assert HE_TO_EN[he] == en

    def test_no_duplicate_hebrew_values(self):
        values = list(EN_TO_HE.values())
        assert len(values) == len(set(values)), "Duplicate Hebrew characters in map"

    def test_bracket_swap(self):
        assert EN_TO_HE['['] == ']'
        assert EN_TO_HE[']'] == '['


class TestDirectionDetection:
    def test_detects_english_text(self):
        assert _detect_direction('hello world') == 'en_to_he'

    def test_detects_hebrew_text(self):
        assert _detect_direction('שלום עולם') == 'he_to_en'

    def test_mixed_majority_hebrew(self):
        assert _detect_direction('שלום ab') == 'he_to_en'

    def test_mixed_majority_english(self):
        assert _detect_direction('hello שב') == 'en_to_he'

    def test_spaces_and_numbers_ignored(self):
        # Only letters count, so "123 abc" → 3 EN, 0 HE → en_to_he
        assert _detect_direction('123 abc') == 'en_to_he'

    def test_empty_defaults_to_en_to_he(self):
        assert _detect_direction('') == 'en_to_he'

    def test_equal_count_defaults_to_en_to_he(self):
        assert _detect_direction('aשbד') == 'en_to_he'


class TestConvertEnToHe:
    def test_simple_word(self):
        # "shalom" in English layout → שלום in Hebrew
        # s→ד, h→י, a→ש, l→ך, o→ם, m→צ  — actually let's check what "shalom" maps to
        result = convert('shalom', 'en_to_he')
        assert result == 'דישךםצ'

    def test_lowercase_and_uppercase_produce_same_hebrew(self):
        lower = convert('abc', 'en_to_he')
        upper = convert('ABC', 'en_to_he')
        assert lower == upper

    def test_spaces_pass_through(self):
        result = convert('hello world', 'en_to_he')
        assert ' ' in result

    def test_numbers_pass_through(self):
        result = convert('abc 123', 'en_to_he')
        assert '1' in result
        assert '2' in result
        assert '3' in result

    def test_unmapped_chars_pass_through(self):
        result = convert('a!b@c', 'en_to_he')
        assert '!' in result
        assert '@' in result

    def test_bracket_conversion(self):
        result = convert('[', 'en_to_he')
        assert result == ']'
        result = convert(']', 'en_to_he')
        assert result == '['

    def test_empty_string(self):
        assert convert('', 'en_to_he') == ''

    def test_single_char_e(self):
        assert convert('e', 'en_to_he') == 'ק'

    def test_single_char_r(self):
        assert convert('r', 'en_to_he') == 'ר'


class TestConvertHeToEn:
    def test_simple_hebrew(self):
        result = convert('ק', 'he_to_en')
        assert result == 'e'

    def test_unmapped_chars_pass_through(self):
        result = convert('א!ב', 'he_to_en')
        assert '!' in result

    def test_spaces_pass_through(self):
        result = convert('ש ד', 'he_to_en')
        assert ' ' in result

    def test_empty_string(self):
        assert convert('', 'he_to_en') == ''

    def test_numbers_pass_through(self):
        result = convert('א 123 ב', 'he_to_en')
        assert '1' in result


class TestRoundTrip:
    """Every character in the map must survive a round-trip."""

    @pytest.mark.parametrize("en_char", EN_TO_HE.keys())
    def test_en_roundtrip(self, en_char):
        he = convert(en_char, 'en_to_he')
        back = convert(he, 'he_to_en')
        assert back == en_char, f"Round-trip failed for '{en_char}': EN→HE→EN gave '{back}'"

    @pytest.mark.parametrize("he_char", HE_TO_EN.keys())
    def test_he_roundtrip(self, he_char):
        en = convert(he_char, 'he_to_en')
        back = convert(en, 'en_to_he')
        assert back == he_char, f"Round-trip failed for '{he_char}': HE→EN→HE gave '{back}'"


class TestAutoDetect:
    def test_auto_english_input(self):
        result_auto = convert('hello', 'auto')
        result_explicit = convert('hello', 'en_to_he')
        assert result_auto == result_explicit

    def test_auto_hebrew_input(self):
        he_text = 'שלום'
        result_auto = convert(he_text, 'auto')
        result_explicit = convert(he_text, 'he_to_en')
        assert result_auto == result_explicit


class TestCustomKeymap:
    def test_custom_override_single_key(self):
        # Override 'e' to map to 'X' instead of 'ק'
        result = convert('e', 'en_to_he', custom_keymap={'e': 'X'})
        assert result == 'X'

    def test_custom_override_does_not_affect_other_keys(self):
        result = convert('r', 'en_to_he', custom_keymap={'e': 'X'})
        assert result == 'ר'

    def test_empty_custom_keymap(self):
        result = convert('e', 'en_to_he', custom_keymap={})
        assert result == 'ק'

    def test_none_custom_keymap(self):
        result = convert('e', 'en_to_he', custom_keymap=None)
        assert result == 'ק'


class TestEdgeCases:
    def test_all_spaces(self):
        assert convert('   ', 'en_to_he') == '   '

    def test_mixed_case_word(self):
        lower = convert('hello', 'en_to_he')
        mixed = convert('HeLLo', 'en_to_he')
        assert lower == mixed

    def test_unknown_direction_raises(self):
        with pytest.raises(ValueError):
            convert('hello', 'invalid_direction')

    def test_newline_passes_through(self):
        result = convert('a\nb', 'en_to_he')
        assert '\n' in result

    def test_tab_passes_through(self):
        result = convert('a\tb', 'en_to_he')
        assert '\t' in result
