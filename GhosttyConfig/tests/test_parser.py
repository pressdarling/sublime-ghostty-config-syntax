"""
Tests for GhosttyConfig/lib/parser.py.

Covers parse_line(), parse_document(), is_in_key_position(), and
is_in_value_position() with normal cases, edge cases, and boundary values.
"""
import sys
import os

# Ensure the repo root is on the path so the GhosttyConfig package is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from GhosttyConfig.lib.parser import (
    ParsedLine,
    Range,
    is_in_key_position,
    is_in_value_position,
    parse_document,
    parse_line,
)


# ---------------------------------------------------------------------------
# parse_line – empty lines
# ---------------------------------------------------------------------------


class TestParseLineEmpty:
    def test_truly_empty_string(self):
        result = parse_line("", 0)
        assert result.type == "empty"
        assert result.line_number == 0
        assert result.raw == ""

    def test_whitespace_only_spaces(self):
        result = parse_line("   ", 5)
        assert result.type == "empty"
        assert result.line_number == 5

    def test_whitespace_only_tabs(self):
        result = parse_line("\t\t", 2)
        assert result.type == "empty"

    def test_mixed_whitespace(self):
        result = parse_line("  \t  ", 0)
        assert result.type == "empty"

    def test_empty_key_and_value_are_none(self):
        result = parse_line("", 0)
        assert result.key is None
        assert result.value is None
        assert result.key_range is None
        assert result.value_range is None


# ---------------------------------------------------------------------------
# parse_line – comment lines
# ---------------------------------------------------------------------------


class TestParseLineComment:
    def test_hash_at_start(self):
        result = parse_line("# This is a comment", 0)
        assert result.type == "comment"
        assert result.raw == "# This is a comment"

    def test_indented_comment(self):
        result = parse_line("  # indented comment", 3)
        assert result.type == "comment"
        assert result.line_number == 3

    def test_hash_only(self):
        result = parse_line("#", 0)
        assert result.type == "comment"

    def test_comment_key_value_are_none(self):
        result = parse_line("# key = value", 0)
        assert result.type == "comment"
        assert result.key is None
        assert result.value is None


# ---------------------------------------------------------------------------
# parse_line – key-value lines
# ---------------------------------------------------------------------------


class TestParseLineKeyValue:
    def test_simple_key_value(self):
        result = parse_line("font-size = 14", 0)
        assert result.type == "keyValue"
        assert result.key == "font-size"
        assert result.value == "14"

    def test_key_value_no_spaces(self):
        result = parse_line("font-size=14", 0)
        assert result.type == "keyValue"
        assert result.key == "font-size"
        assert result.value == "14"

    def test_value_with_equals_sign(self):
        result = parse_line("keybind = ctrl+a=select_all", 0)
        assert result.type == "keyValue"
        assert result.key == "keybind"
        assert result.value == "ctrl+a=select_all"

    def test_value_trimmed(self):
        result = parse_line("theme =   dark  ", 0)
        assert result.type == "keyValue"
        assert result.value == "dark"

    def test_empty_value(self):
        result = parse_line("env = ", 0)
        assert result.type == "keyValue"
        assert result.key == "env"
        assert result.value == ""

    def test_hyphenated_key(self):
        result = parse_line("window-padding-x = 10", 0)
        assert result.type == "keyValue"
        assert result.key == "window-padding-x"

    def test_underscore_key(self):
        # Keys can contain underscores per the regex [a-zA-Z0-9_-]*
        result = parse_line("font_size = 14", 0)
        assert result.type == "keyValue"
        assert result.key == "font_size"

    def test_line_number_stored(self):
        result = parse_line("background = #000000", 7)
        assert result.line_number == 7

    def test_raw_stored(self):
        raw = "font-size = 14"
        result = parse_line(raw, 0)
        assert result.raw == raw

    def test_key_range_no_indent(self):
        result = parse_line("key = val", 0)
        assert result.key_range is not None
        assert result.key_range.start == 0
        assert result.key_range.end == 3  # len("key")

    def test_key_range_with_indent(self):
        result = parse_line("  key = val", 0)
        assert result.key_range is not None
        assert result.key_range.start == 2
        assert result.key_range.end == 5  # 2 + len("key")

    def test_value_range_start_after_equals_and_space(self):
        # "key = val"
        #  0123456789
        # equals at index 4, space after =, value "val" starts at 6
        result = parse_line("key = val", 0)
        assert result.value_range is not None
        assert result.value_range.start == 6

    def test_value_range_start_no_space_after_equals(self):
        # "key=val"
        #  0123456
        # equals at index 3, no space, value starts at 4
        result = parse_line("key=val", 0)
        assert result.value_range is not None
        assert result.value_range.start == 4

    def test_value_range_end(self):
        result = parse_line("key = val", 0)
        # "val" ends at index 9 (len("key = val"))
        assert result.value_range is not None
        assert result.value_range.end == 9

    def test_value_range_end_ignores_trailing_whitespace(self):
        # Trailing whitespace stripped in value_end calculation
        result = parse_line("key = val   ", 0)
        assert result.value_range is not None
        assert result.value_range.end == 9  # "val" ends at 9

    def test_color_value(self):
        result = parse_line("background = #282c34", 0)
        assert result.type == "keyValue"
        assert result.value == "#282c34"

    def test_path_value(self):
        result = parse_line("config-file = ~/.config/ghostty/local.conf", 0)
        assert result.type == "keyValue"
        assert result.value == "~/.config/ghostty/local.conf"


# ---------------------------------------------------------------------------
# parse_line – invalid lines
# ---------------------------------------------------------------------------


class TestParseLineInvalid:
    def test_starts_with_equals(self):
        result = parse_line("=invalid", 0)
        assert result.type == "invalid"

    def test_starts_with_digit(self):
        result = parse_line("123 = value", 0)
        assert result.type == "invalid"

    def test_plain_word_no_equals(self):
        # A bare word without '=' is invalid per the regex
        result = parse_line("justword", 0)
        assert result.type == "invalid"

    def test_invalid_key_and_value_are_none(self):
        result = parse_line("=invalid", 0)
        assert result.key is None
        assert result.value is None
        assert result.key_range is None
        assert result.value_range is None


# ---------------------------------------------------------------------------
# parse_document
# ---------------------------------------------------------------------------


class TestParseDocument:
    def test_single_line(self):
        results = parse_document("font-size = 14")
        assert len(results) == 1
        assert results[0].key == "font-size"

    def test_multiple_lines(self):
        text = "font-size = 14\nbackground = #000000\ntheme = dark"
        results = parse_document(text)
        assert len(results) == 3
        assert results[0].key == "font-size"
        assert results[1].key == "background"
        assert results[2].key == "theme"

    def test_line_numbers_sequential(self):
        text = "# comment\nfont-size = 14\n\nbackground = #000"
        results = parse_document(text)
        assert results[0].line_number == 0
        assert results[1].line_number == 1
        assert results[2].line_number == 2
        assert results[3].line_number == 3

    def test_filters_correctly(self):
        text = "# comment\nfont-size = 14\n\nbackground = #000"
        results = parse_document(text)
        key_values = [r for r in results if r.type == "keyValue"]
        assert len(key_values) == 2

    def test_empty_document(self):
        results = parse_document("")
        assert len(results) == 1
        assert results[0].type == "empty"

    def test_multiple_keybinds(self):
        text = (
            "keybind = ctrl+c=copy_to_clipboard\n"
            "keybind = ctrl+v=paste_from_clipboard\n"
            "keybind = ctrl+t=new_tab"
        )
        results = parse_document(text)
        key_values = [r for r in results if r.type == "keyValue"]
        assert len(key_values) == 3
        assert all(r.key == "keybind" for r in key_values)

    def test_mixed_content(self):
        text = "# header\nfont-size = 14\n\n# color settings\nbackground = black"
        results = parse_document(text)
        assert results[0].type == "comment"
        assert results[1].type == "keyValue"
        assert results[2].type == "empty"
        assert results[3].type == "comment"
        assert results[4].type == "keyValue"

    def test_returns_list_of_parsed_lines(self):
        results = parse_document("key = value")
        assert isinstance(results, list)
        assert all(isinstance(r, ParsedLine) for r in results)


# ---------------------------------------------------------------------------
# is_in_key_position
# ---------------------------------------------------------------------------


class TestIsInKeyPosition:
    def test_before_equals(self):
        # "key = val", equals at index 4
        assert is_in_key_position("key = val", 2) is True

    def test_at_equals(self):
        assert is_in_key_position("key = val", 4) is True

    def test_after_equals(self):
        assert is_in_key_position("key = val", 5) is False

    def test_value_portion(self):
        assert is_in_key_position("key = val", 8) is False

    def test_no_equals_always_key(self):
        assert is_in_key_position("justword", 5) is True

    def test_no_equals_at_end(self):
        assert is_in_key_position("word", 4) is True

    def test_at_position_zero(self):
        assert is_in_key_position("key = val", 0) is True

    def test_empty_line(self):
        assert is_in_key_position("", 0) is True

    def test_equals_at_start(self):
        # equals at index 0, character <= 0 is True only for character==0
        assert is_in_key_position("=val", 0) is True
        assert is_in_key_position("=val", 1) is False


# ---------------------------------------------------------------------------
# is_in_value_position
# ---------------------------------------------------------------------------


class TestIsInValuePosition:
    def test_after_equals(self):
        # "key = val", equals at index 4, character 6 is in value
        assert is_in_value_position("key = val", 6) is True

    def test_before_equals(self):
        assert is_in_value_position("key = val", 2) is False

    def test_at_equals(self):
        # character <= equals_index → not value position
        assert is_in_value_position("key = val", 4) is False

    def test_no_equals(self):
        assert is_in_value_position("justword", 5) is False

    def test_empty_line(self):
        assert is_in_value_position("", 0) is False

    def test_immediately_after_equals(self):
        assert is_in_value_position("k=v", 2) is True

    def test_equals_at_start_character_1(self):
        assert is_in_value_position("=val", 1) is True

    def test_equals_at_start_character_0(self):
        assert is_in_value_position("=val", 0) is False

    def test_complementary_to_key_position_at_boundary(self):
        """Positions that are key-position should NOT be value-position."""
        line = "font-size = 14"
        eq = line.index("=")
        # At the equals sign itself: key position True, value position False
        assert is_in_key_position(line, eq) is True
        assert is_in_value_position(line, eq) is False
        # One past: key position False, value position True
        assert is_in_key_position(line, eq + 1) is False
        assert is_in_value_position(line, eq + 1) is True