"""
Tests for GhosttyConfig/lib/completion.py.

Covers GhosttyCompletionEngine.completions_for(), _key_completions(), and
_value_completions() for all supported option types and edge cases.

The sublime module is mocked via conftest.py before this module is imported.
"""
import os
import sys

import pytest

# Ensure the repo root is on the path so the GhosttyConfig package is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# conftest.py installs the sublime mock before this import executes.
from GhosttyConfig.lib.completion import GhosttyCompletionEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _triggers(items):
    """Extract trigger strings from a list of CompletionItem objects."""
    return [item.trigger for item in items]


def _completions(items):
    """Extract completion strings from a list of CompletionItem objects."""
    return [item.completion for item in items]


# ---------------------------------------------------------------------------
# GhosttyCompletionEngine.__init__
# ---------------------------------------------------------------------------


class TestInit:
    def test_stores_schema(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        assert engine.schema is minimal_schema

    def test_empty_schema(self):
        engine = GhosttyCompletionEngine({})
        assert engine.schema == {}


# ---------------------------------------------------------------------------
# completions_for – early exit conditions
# ---------------------------------------------------------------------------


class TestCompletionsForEarlyExit:
    def test_comment_line_returns_empty(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        result = engine.completions_for("# this is a comment", 5)
        assert result == []

    def test_comment_with_leading_space_returns_empty(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        result = engine.completions_for("  # indented comment", 10)
        assert result == []

    def test_empty_schema_key_position_returns_empty(self):
        engine = GhosttyCompletionEngine({})
        result = engine.completions_for("font", 4)
        assert result == []

    def test_empty_schema_value_position_returns_empty(self):
        engine = GhosttyCompletionEngine({})
        result = engine.completions_for("font-size = ", 12)
        assert result == []


# ---------------------------------------------------------------------------
# completions_for – key position routing
# ---------------------------------------------------------------------------


class TestCompletionsForKeyPosition:
    def test_returns_items_for_key_position(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        # cursor before '=': key position
        items = engine.completions_for("font", 4)
        assert len(items) > 0

    def test_key_completions_include_matching_key(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine.completions_for("font-size", 9)
        triggers = _triggers(items)
        assert "font-size" in triggers

    def test_key_completions_filtered_by_prefix(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        # "cursor" should match cursor-style and cursor-style-blink
        items = engine.completions_for("cursor", 6)
        triggers = _triggers(items)
        assert all("cursor" in t for t in triggers)

    def test_key_completions_no_prefix_returns_all(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine.completions_for("", 0)
        assert len(items) == len(minimal_schema["options"])


# ---------------------------------------------------------------------------
# completions_for – value position routing
# ---------------------------------------------------------------------------


class TestCompletionsForValuePosition:
    def test_returns_items_for_value_position(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        # cursor after '=': value position
        items = engine.completions_for("cursor-style = ", 15)
        assert len(items) > 0

    def test_unknown_key_returns_empty(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine.completions_for("unknown-key = ", 14)
        assert items == []

    def test_value_position_routes_to_boolean(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine.completions_for("cursor-style-blink = ", 21)
        triggers = _triggers(items)
        assert "true" in triggers
        assert "false" in triggers


# ---------------------------------------------------------------------------
# _key_completions
# ---------------------------------------------------------------------------


class TestKeyCompletions:
    def test_completion_insert_includes_equals(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._key_completions("")
        for item in items:
            assert item.completion.endswith(" = ")

    def test_completion_trigger_is_key_name(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._key_completions("")
        triggers = _triggers(items)
        assert "font-size" in triggers
        assert "background" in triggers

    def test_annotation_is_type(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._key_completions("")
        by_trigger = {item.trigger: item for item in items}
        assert by_trigger["font-size"].annotation == "number"
        assert by_trigger["background"].annotation == "color"

    def test_repeatable_annotation_appended(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._key_completions("")
        by_trigger = {item.trigger: item for item in items}
        # font-family has repeatable=True in options
        assert "(repeatable)" in by_trigger["font-family"].annotation

    def test_repeatable_key_from_repeatableKeys_list(self, minimal_schema):
        """A key listed in repeatableKeys but not with repeatable: True in options."""
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._key_completions("")
        by_trigger = {item.trigger: item for item in items}
        # 'keybind' is in repeatableKeys AND has repeatable=True in options
        assert "(repeatable)" in by_trigger["keybind"].annotation

    def test_non_repeatable_key_no_annotation_suffix(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._key_completions("")
        by_trigger = {item.trigger: item for item in items}
        # font-size is not repeatable
        assert "(repeatable)" not in by_trigger["font-size"].annotation

    def test_details_is_description(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._key_completions("")
        by_trigger = {item.trigger: item for item in items}
        assert by_trigger["font-size"].details == "Font size in points."

    def test_prefix_filter_case_insensitive(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items_lower = engine._key_completions("cursor")
        items_upper = engine._key_completions("CURSOR")
        assert _triggers(items_lower) == _triggers(items_upper)

    def test_empty_prefix_returns_all_options(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._key_completions("")
        assert len(items) == len(minimal_schema["options"])

    def test_nonmatching_prefix_returns_empty(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._key_completions("zzzznotakey")
        assert items == []

    def test_type_defaults_to_string_when_missing(self):
        schema = {"options": {"my-key": {"description": "No type field."}}}
        engine = GhosttyCompletionEngine(schema)
        items = engine._key_completions("")
        assert items[0].annotation == "string"


# ---------------------------------------------------------------------------
# _value_completions – boolean type
# ---------------------------------------------------------------------------


class TestValueCompletionsBoolean:
    def test_boolean_values(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._value_completions("cursor-style-blink", "cursor-style-blink = ")
        triggers = _triggers(items)
        assert triggers == ["true", "false"]

    def test_boolean_filtered_by_partial_true(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._value_completions(
            "cursor-style-blink", "cursor-style-blink = tr"
        )
        triggers = _triggers(items)
        assert "true" in triggers
        assert "false" not in triggers

    def test_boolean_filtered_by_partial_false(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._value_completions(
            "cursor-style-blink", "cursor-style-blink = fal"
        )
        triggers = _triggers(items)
        assert "false" in triggers
        assert "true" not in triggers


# ---------------------------------------------------------------------------
# _value_completions – enum type
# ---------------------------------------------------------------------------


class TestValueCompletionsEnum:
    def test_enum_returns_all_values(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._value_completions("cursor-style", "cursor-style = ")
        triggers = _triggers(items)
        assert set(triggers) == {"block", "bar", "underline", "block_hollow"}

    def test_enum_filtered_by_partial(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._value_completions("cursor-style", "cursor-style = bl")
        triggers = _triggers(items)
        assert "block" in triggers
        assert "block_hollow" in triggers
        assert "bar" not in triggers
        assert "underline" not in triggers

    def test_empty_enum_list(self):
        schema = {"options": {"my-enum": {"type": "enum", "enum": []}}}
        engine = GhosttyCompletionEngine(schema)
        items = engine._value_completions("my-enum", "my-enum = ")
        assert items == []


# ---------------------------------------------------------------------------
# _value_completions – color type
# ---------------------------------------------------------------------------


class TestValueCompletionsColor:
    def test_color_includes_hash_prefix(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._value_completions("background", "background = ")
        triggers = _triggers(items)
        assert "#" in triggers

    def test_color_includes_named_values(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._value_completions("background", "background = ")
        triggers = _triggers(items)
        assert "black" in triggers
        assert "white" in triggers

    def test_color_filtered_by_partial(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._value_completions("background", "background = bl")
        triggers = _triggers(items)
        assert "black" in triggers
        assert "white" not in triggers

    def test_color_no_types_section(self):
        schema = {
            "options": {"fg": {"type": "color"}},
            # No "types" key
        }
        engine = GhosttyCompletionEngine(schema)
        items = engine._value_completions("fg", "fg = ")
        triggers = _triggers(items)
        # Should still return "#" at minimum
        assert "#" in triggers

    def test_color_no_named_values(self):
        schema = {
            "options": {"fg": {"type": "color"}},
            "types": {"color": {}},  # No namedValues
        }
        engine = GhosttyCompletionEngine(schema)
        items = engine._value_completions("fg", "fg = ")
        triggers = _triggers(items)
        assert triggers == ["#"]


# ---------------------------------------------------------------------------
# _value_completions – keybind type
# ---------------------------------------------------------------------------


class TestValueCompletionsKeybind:
    def test_keybind_includes_modifiers_with_plus(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._value_completions("keybind", "keybind = ")
        triggers = _triggers(items)
        assert "shift+" in triggers
        assert "ctrl+" in triggers
        assert "alt+" in triggers

    def test_keybind_includes_prefixes_with_colon(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._value_completions("keybind", "keybind = ")
        triggers = _triggers(items)
        assert "global:" in triggers
        assert "all:" in triggers

    def test_keybind_includes_clear(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._value_completions("keybind", "keybind = ")
        triggers = _triggers(items)
        assert "clear" in triggers

    def test_keybind_filtered_by_partial(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._value_completions("keybind", "keybind = sh")
        triggers = _triggers(items)
        assert "shift+" in triggers
        # "ctrl+" does not contain "sh"
        assert "ctrl+" not in triggers

    def test_keybind_no_types_section(self):
        schema = {
            "options": {"keybind": {"type": "keybind"}},
            # No "types" key
        }
        engine = GhosttyCompletionEngine(schema)
        items = engine._value_completions("keybind", "keybind = ")
        triggers = _triggers(items)
        # Only "clear" remains when modifiers/prefixes are empty
        assert "clear" in triggers


# ---------------------------------------------------------------------------
# _value_completions – fallback to examples
# ---------------------------------------------------------------------------


class TestValueCompletionsExamples:
    def test_string_type_uses_examples(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._value_completions("theme", "theme = ")
        triggers = _triggers(items)
        assert "auto" in triggers
        assert "Catppuccin Mocha" in triggers

    def test_number_type_uses_examples(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._value_completions("font-size", "font-size = ")
        triggers = _triggers(items)
        assert "12" in triggers
        assert "14" in triggers

    def test_examples_filtered_by_partial(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._value_completions("font-size", "font-size = 1")
        triggers = _triggers(items)
        assert "12" in triggers
        assert "14" in triggers
        # "16" also contains "1" so it should be included too
        assert "16" in triggers

    def test_no_examples_returns_empty(self):
        schema = {"options": {"my-key": {"type": "string"}}}
        engine = GhosttyCompletionEngine(schema)
        items = engine._value_completions("my-key", "my-key = ")
        assert items == []


# ---------------------------------------------------------------------------
# _value_completions – unknown key
# ---------------------------------------------------------------------------


class TestValueCompletionsUnknownKey:
    def test_unknown_key_returns_empty(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        result = engine._value_completions("not-a-real-key", "not-a-real-key = ")
        assert result == []

    def test_empty_options_returns_empty(self):
        engine = GhosttyCompletionEngine({})
        result = engine._value_completions("font-size", "font-size = ")
        assert result == []


# ---------------------------------------------------------------------------
# _value_completions – partial value extraction
# ---------------------------------------------------------------------------


class TestValuePartialExtraction:
    def test_partial_value_after_equals(self, minimal_schema):
        """Partial after '=' is used for filtering."""
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._value_completions("cursor-style", "cursor-style = bar")
        triggers = _triggers(items)
        assert "bar" in triggers
        assert "block" not in triggers

    def test_no_equals_partial_is_empty(self, minimal_schema):
        """When text_before_cursor has no '=', partial is '' (all returned)."""
        engine = GhosttyCompletionEngine(minimal_schema)
        # Without '=' present in text_before_cursor, partial = ""
        items = engine._value_completions("cursor-style", "cursor-style")
        triggers = _triggers(items)
        assert set(triggers) == {"block", "bar", "underline", "block_hollow"}

    def test_completion_trigger_matches_value(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine._value_completions("cursor-style", "cursor-style = ")
        for item in items:
            assert item.trigger == item.completion


# ---------------------------------------------------------------------------
# completions_for – integration (key + value routing together)
# ---------------------------------------------------------------------------


class TestCompletionsForIntegration:
    def test_key_position_at_zero(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        # Empty line, cursor at 0: key position
        items = engine.completions_for("", 0)
        assert len(items) == len(minimal_schema["options"])

    def test_value_position_for_boolean(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        line = "cursor-style-blink = "
        items = engine.completions_for(line, len(line))
        triggers = _triggers(items)
        assert set(triggers) == {"true", "false"}

    def test_value_position_for_enum(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        line = "cursor-style = "
        items = engine.completions_for(line, len(line))
        triggers = _triggers(items)
        assert "block" in triggers

    def test_hash_only_comment_returns_empty(self, minimal_schema):
        engine = GhosttyCompletionEngine(minimal_schema)
        items = engine.completions_for("#", 1)
        assert items == []