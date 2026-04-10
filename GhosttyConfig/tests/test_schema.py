"""
Tests for GhosttyConfig/lib/schema.py.

Covers load_schema() with valid schemas, invalid JSON, non-dict JSON, missing
files, and the actual bundled schema file.
"""
import json
import os
import sys
import tempfile

import pytest

# Ensure the repo root is on the path so the GhosttyConfig package is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from GhosttyConfig.lib.schema import SCHEMA_RELATIVE_PATH, load_schema


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_schema(tmp_dir: str, content: str) -> str:
    """Write a schema file in the expected location and return the package path."""
    schema_dir = os.path.join(tmp_dir, "schema")
    os.makedirs(schema_dir, exist_ok=True)
    schema_file = os.path.join(schema_dir, "ghostty-config-syntax.schema.json")
    with open(schema_file, "w", encoding="utf-8") as fh:
        fh.write(content)
    return tmp_dir


# ---------------------------------------------------------------------------
# load_schema – valid input
# ---------------------------------------------------------------------------


class TestLoadSchemaValid:
    def test_returns_dict_for_valid_json(self, tmp_path):
        data = {"options": {"font-size": {"type": "number"}}}
        _write_schema(str(tmp_path), json.dumps(data))
        result = load_schema(str(tmp_path))
        assert isinstance(result, dict)
        assert "options" in result

    def test_options_preserved(self, tmp_path):
        data = {
            "options": {
                "font-size": {"type": "number", "description": "Font size."},
                "background": {"type": "color"},
            }
        }
        _write_schema(str(tmp_path), json.dumps(data))
        result = load_schema(str(tmp_path))
        assert "font-size" in result["options"]
        assert "background" in result["options"]

    def test_repeatable_keys_preserved(self, tmp_path):
        data = {
            "repeatableKeys": ["keybind", "palette"],
            "options": {},
        }
        _write_schema(str(tmp_path), json.dumps(data))
        result = load_schema(str(tmp_path))
        assert result["repeatableKeys"] == ["keybind", "palette"]

    def test_nested_types_preserved(self, tmp_path):
        data = {
            "options": {},
            "types": {
                "color": {"namedValues": ["black", "white"]},
            },
        }
        _write_schema(str(tmp_path), json.dumps(data))
        result = load_schema(str(tmp_path))
        assert result["types"]["color"]["namedValues"] == ["black", "white"]

    def test_utf8_content(self, tmp_path):
        data = {"description": "Ghostty terminal – configuration schema"}
        _write_schema(str(tmp_path), json.dumps(data, ensure_ascii=False))
        result = load_schema(str(tmp_path))
        assert "–" in result["description"]


# ---------------------------------------------------------------------------
# load_schema – non-dict JSON
# ---------------------------------------------------------------------------


class TestLoadSchemaNonDict:
    def test_json_list_returns_empty_dict(self, tmp_path):
        _write_schema(str(tmp_path), json.dumps(["item1", "item2"]))
        result = load_schema(str(tmp_path))
        assert result == {}

    def test_json_string_returns_empty_dict(self, tmp_path):
        _write_schema(str(tmp_path), json.dumps("just a string"))
        result = load_schema(str(tmp_path))
        assert result == {}

    def test_json_number_returns_empty_dict(self, tmp_path):
        _write_schema(str(tmp_path), "42")
        result = load_schema(str(tmp_path))
        assert result == {}

    def test_json_null_returns_empty_dict(self, tmp_path):
        _write_schema(str(tmp_path), "null")
        result = load_schema(str(tmp_path))
        assert result == {}

    def test_json_bool_returns_empty_dict(self, tmp_path):
        _write_schema(str(tmp_path), "true")
        result = load_schema(str(tmp_path))
        assert result == {}


# ---------------------------------------------------------------------------
# load_schema – invalid JSON
# ---------------------------------------------------------------------------


class TestLoadSchemaInvalidJson:
    def test_malformed_json_returns_empty_dict(self, tmp_path):
        _write_schema(str(tmp_path), "{this is not valid json}")
        result = load_schema(str(tmp_path))
        assert result == {}

    def test_truncated_json_returns_empty_dict(self, tmp_path):
        _write_schema(str(tmp_path), '{"options": {')
        result = load_schema(str(tmp_path))
        assert result == {}

    def test_empty_file_returns_empty_dict(self, tmp_path):
        _write_schema(str(tmp_path), "")
        result = load_schema(str(tmp_path))
        assert result == {}


# ---------------------------------------------------------------------------
# load_schema – missing file
# ---------------------------------------------------------------------------


class TestLoadSchemaMissingFile:
    def test_nonexistent_directory_returns_empty_dict(self, tmp_path):
        nonexistent = str(tmp_path / "does_not_exist")
        result = load_schema(nonexistent)
        assert result == {}

    def test_nonexistent_schema_file_returns_empty_dict(self, tmp_path):
        # Directory exists but schema file is absent
        schema_dir = tmp_path / "schema"
        schema_dir.mkdir()
        result = load_schema(str(tmp_path))
        assert result == {}

    def test_path_with_no_schema_subdir_returns_empty_dict(self, tmp_path):
        # tmp_path has no schema/ subdirectory at all
        result = load_schema(str(tmp_path))
        assert result == {}


# ---------------------------------------------------------------------------
# load_schema – SCHEMA_RELATIVE_PATH constant
# ---------------------------------------------------------------------------


class TestSchemaRelativePath:
    def test_relative_path_includes_schema_filename(self):
        assert "ghostty-config-syntax.schema.json" in SCHEMA_RELATIVE_PATH

    def test_relative_path_includes_schema_directory(self):
        assert "schema" in SCHEMA_RELATIVE_PATH


# ---------------------------------------------------------------------------
# load_schema – against the actual bundled schema
# ---------------------------------------------------------------------------


class TestLoadSchemaActualFile:
    """Integration-level: load the real bundled schema and verify structure."""

    @pytest.fixture()
    def actual_package_path(self):
        # The schema lives at GhosttyConfig/schema/...
        return os.path.join(os.path.dirname(__file__), "..")

    def test_loads_actual_schema(self, actual_package_path):
        result = load_schema(actual_package_path)
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_actual_schema_has_options(self, actual_package_path):
        result = load_schema(actual_package_path)
        assert "options" in result
        assert len(result["options"]) > 0

    def test_actual_schema_has_font_size(self, actual_package_path):
        result = load_schema(actual_package_path)
        assert "font-size" in result["options"]

    def test_actual_schema_has_background(self, actual_package_path):
        result = load_schema(actual_package_path)
        assert "background" in result["options"]

    def test_actual_schema_has_keybind(self, actual_package_path):
        result = load_schema(actual_package_path)
        assert "keybind" in result["options"]

    def test_actual_schema_repeatable_keys(self, actual_package_path):
        result = load_schema(actual_package_path)
        assert "repeatableKeys" in result
        assert "keybind" in result["repeatableKeys"]
        assert "palette" in result["repeatableKeys"]
        assert "font-family" in result["repeatableKeys"]

    def test_actual_schema_types(self, actual_package_path):
        result = load_schema(actual_package_path)
        assert "types" in result
        assert "color" in result["types"]
        assert "keybind" in result["types"]

    def test_actual_schema_font_size_type(self, actual_package_path):
        result = load_schema(actual_package_path)
        assert result["options"]["font-size"]["type"] == "number"

    def test_actual_schema_background_type(self, actual_package_path):
        result = load_schema(actual_package_path)
        assert result["options"]["background"]["type"] == "color"

    def test_actual_schema_keybind_repeatable(self, actual_package_path):
        result = load_schema(actual_package_path)
        keybind = result["options"]["keybind"]
        assert keybind.get("repeatable") is True or "keybind" in result.get("repeatableKeys", [])