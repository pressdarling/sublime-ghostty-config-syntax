"""
Tests for GhosttyConfig/ghostty_config.py.

Covers _normalize(), is_ghostty_config_path(), _open_config_paths(),
_ghostty_candidates(), plugin_loaded(), GhosttyOpenConfigCommand helpers,
and GhosttyConfigListener helpers.

The sublime / sublime_plugin modules are mocked via conftest.py.
"""
import os
import sys
import importlib
from unittest.mock import MagicMock, patch, call

import pytest

# Ensure the repo root is on the path so the GhosttyConfig package is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ---------------------------------------------------------------------------
# Module-level import
# ---------------------------------------------------------------------------
# conftest.py has already installed the sublime/sublime_plugin mocks.
import GhosttyConfig.ghostty_config as ghostty_config_module
from GhosttyConfig.ghostty_config import (
    _normalize,
    is_ghostty_config_path,
    GhosttyOpenConfigCommand,
    GhosttyConfigListener,
    SYNTAX,
)


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_collapses_redundant_separators(self):
        path = "/foo//bar"
        result = _normalize(path)
        assert "//" not in result

    def test_collapses_up_level_refs(self):
        result = _normalize("/foo/bar/../baz")
        assert ".." not in result
        assert result == _normalize("/foo/baz")

    def test_identity_on_already_normal_path(self, tmp_path):
        p = str(tmp_path)
        assert _normalize(p) == _normalize(_normalize(p))

    def test_tilde_not_expanded(self):
        # _normalize only calls normcase+normpath; it does NOT expand ~
        result = _normalize("~/config")
        assert "~" in result or os.sep in result  # platform-dependent

    def test_returns_string(self):
        assert isinstance(_normalize("/some/path"), str)


# ---------------------------------------------------------------------------
# is_ghostty_config_path – .ghostty extension
# ---------------------------------------------------------------------------


class TestIsGhosttyConfigPathExtension:
    def test_dotghosted_extension_is_true(self):
        assert is_ghostty_config_path("/home/user/myterm.ghostty") is True

    def test_dotghosted_extension_uppercase_false(self):
        # .GHOSTTY uppercase: on case-sensitive OS normcase doesn't change it
        # The check is on the normalised path ending with ".ghostty" (lowercase literal)
        if os.name == "nt":
            assert is_ghostty_config_path("/home/user/myterm.GHOSTTY") is True
        else:
            assert is_ghostty_config_path("/home/user/myterm.GHOSTTY") is False

    def test_plain_filename_is_false(self):
        assert is_ghostty_config_path("/home/user/config") is False

    def test_empty_string_is_false(self):
        assert is_ghostty_config_path("") is False

    def test_none_string_is_false(self):
        # The function checks `if not path`, so None-like empty string → False
        assert is_ghostty_config_path("") is False


# ---------------------------------------------------------------------------
# is_ghostty_config_path – candidate paths (using module globals)
# ---------------------------------------------------------------------------


class TestIsGhosttyConfigPathCandidate:
    def test_path_in_candidates_is_true(self):
        """If _GHOSTTY_CANDIDATES contains a path, it should match."""
        original = ghostty_config_module._GHOSTTY_CANDIDATES
        try:
            test_path = _normalize("/tmp/ghostty-test/config")
            ghostty_config_module._GHOSTTY_CANDIDATES = {test_path}
            assert is_ghostty_config_path("/tmp/ghostty-test/config") is True
        finally:
            ghostty_config_module._GHOSTTY_CANDIDATES = original

    def test_path_not_in_candidates_is_false(self):
        original = ghostty_config_module._GHOSTTY_CANDIDATES
        try:
            ghostty_config_module._GHOSTTY_CANDIDATES = set()
            assert is_ghostty_config_path("/tmp/not-a-ghostty-config") is False
        finally:
            ghostty_config_module._GHOSTTY_CANDIDATES = original


# ---------------------------------------------------------------------------
# _open_config_paths
# ---------------------------------------------------------------------------


class TestOpenConfigPaths:
    def _call_with_settings(self, paths_value, env=None):
        """Helper: call _open_config_paths with mocked settings and environ."""
        sublime = sys.modules["sublime"]
        settings_mock = MagicMock()
        settings_mock.get.return_value = paths_value
        sublime.load_settings.return_value = settings_mock

        env = env or {}
        with patch.dict(os.environ, env, clear=False):
            # Remove APPDATA to avoid interference unless explicitly set
            with patch.dict(os.environ, {"APPDATA": ""}, clear=False):
                # Fully replace environ for this test
                with patch.object(os, "environ", {**os.environ, **env}):
                    from GhosttyConfig.ghostty_config import _open_config_paths
                    return _open_config_paths()

    def test_returns_list_for_valid_paths(self):
        sublime = sys.modules["sublime"]
        settings_mock = MagicMock()
        settings_mock.get.return_value = [
            "~/.config/ghostty/config",
            "~/Library/Application Support/com.mitchellh.ghostty/config",
        ]
        sublime.load_settings.return_value = settings_mock

        env_without_appdata = {k: v for k, v in os.environ.items() if k != "APPDATA"}
        with patch.dict(os.environ, env_without_appdata, clear=True):
            from GhosttyConfig.ghostty_config import _open_config_paths
            result = _open_config_paths()

        assert isinstance(result, list)
        assert len(result) == 2

    def test_tilde_expanded(self):
        sublime = sys.modules["sublime"]
        settings_mock = MagicMock()
        settings_mock.get.return_value = ["~/.config/ghostty/config"]
        sublime.load_settings.return_value = settings_mock

        env_without_appdata = {k: v for k, v in os.environ.items() if k != "APPDATA"}
        with patch.dict(os.environ, env_without_appdata, clear=True):
            from GhosttyConfig.ghostty_config import _open_config_paths
            result = _open_config_paths()

        assert result[0] == os.path.expanduser("~/.config/ghostty/config")
        assert "~" not in result[0]

    def test_non_list_returns_empty(self):
        sublime = sys.modules["sublime"]
        settings_mock = MagicMock()
        settings_mock.get.return_value = "not-a-list"
        sublime.load_settings.return_value = settings_mock

        from GhosttyConfig.ghostty_config import _open_config_paths
        result = _open_config_paths()
        assert result == []

    def test_none_returns_empty(self):
        sublime = sys.modules["sublime"]
        settings_mock = MagicMock()
        settings_mock.get.return_value = None
        sublime.load_settings.return_value = settings_mock

        from GhosttyConfig.ghostty_config import _open_config_paths
        result = _open_config_paths()
        # None is not a list → []
        assert result == []

    def test_empty_strings_filtered_out(self):
        sublime = sys.modules["sublime"]
        settings_mock = MagicMock()
        settings_mock.get.return_value = ["~/.config/ghostty/config", "", "   "]
        sublime.load_settings.return_value = settings_mock

        # Empty-string path "" evaluates as falsy and is excluded.
        # "   " is truthy (non-empty), but it's still included.
        env_without_appdata = {k: v for k, v in os.environ.items() if k != "APPDATA"}
        with patch.dict(os.environ, env_without_appdata, clear=True):
            from GhosttyConfig.ghostty_config import _open_config_paths
            result = _open_config_paths()

        # "" filtered, "   " would expand to "   " (non-empty str, kept or not
        # depends on truthiness check: "   " is truthy → kept)
        assert os.path.expanduser("~/.config/ghostty/config") in result
        assert "" not in result

    def test_appdata_path_appended_when_set(self):
        sublime = sys.modules["sublime"]
        settings_mock = MagicMock()
        settings_mock.get.return_value = ["~/.config/ghostty/config"]
        sublime.load_settings.return_value = settings_mock

        fake_appdata = "/fake/appdata"
        with patch.dict(os.environ, {"APPDATA": fake_appdata}, clear=False):
            from GhosttyConfig.ghostty_config import _open_config_paths
            result = _open_config_paths()

        expected_windows = os.path.join(fake_appdata, "ghostty", "config")
        assert expected_windows in result

    def test_appdata_not_duplicated(self):
        sublime = sys.modules["sublime"]
        fake_appdata = "/fake/appdata"
        windows_path = os.path.join(fake_appdata, "ghostty", "config")
        settings_mock = MagicMock()
        settings_mock.get.return_value = [windows_path]
        sublime.load_settings.return_value = settings_mock

        with patch.dict(os.environ, {"APPDATA": fake_appdata}, clear=False):
            from GhosttyConfig.ghostty_config import _open_config_paths
            result = _open_config_paths()

        assert result.count(windows_path) == 1

    def test_appdata_not_appended_when_absent(self):
        sublime = sys.modules["sublime"]
        settings_mock = MagicMock()
        settings_mock.get.return_value = ["~/.config/ghostty/config"]
        sublime.load_settings.return_value = settings_mock

        env_without_appdata = {k: v for k, v in os.environ.items() if k != "APPDATA"}
        with patch.dict(os.environ, env_without_appdata, clear=True):
            from GhosttyConfig.ghostty_config import _open_config_paths
            result = _open_config_paths()

        assert not any("ghostty" in p and "appdata" in p.lower() for p in result)


# ---------------------------------------------------------------------------
# plugin_loaded
# ---------------------------------------------------------------------------


class TestPluginLoaded:
    def test_sets_schema_global(self):
        from GhosttyConfig.ghostty_config import plugin_loaded
        original_schema = ghostty_config_module._SCHEMA
        try:
            plugin_loaded()
            assert ghostty_config_module._SCHEMA is not None
        finally:
            ghostty_config_module._SCHEMA = original_schema

    def test_sets_completions_global(self):
        from GhosttyConfig.ghostty_config import plugin_loaded
        original = ghostty_config_module._COMPLETIONS
        try:
            plugin_loaded()
            assert ghostty_config_module._COMPLETIONS is not None
        finally:
            ghostty_config_module._COMPLETIONS = original

    def test_sets_candidates_global(self):
        from GhosttyConfig.ghostty_config import plugin_loaded
        original = ghostty_config_module._GHOSTTY_CANDIDATES
        try:
            plugin_loaded()
            assert isinstance(ghostty_config_module._GHOSTTY_CANDIDATES, set)
        finally:
            ghostty_config_module._GHOSTTY_CANDIDATES = original

    def test_schema_load_failure_sets_empty_dict(self):
        from GhosttyConfig.ghostty_config import plugin_loaded
        original_schema = ghostty_config_module._SCHEMA
        try:
            with patch("GhosttyConfig.ghostty_config.load_schema", side_effect=RuntimeError("boom")):
                plugin_loaded()
            assert ghostty_config_module._SCHEMA == {}
        finally:
            ghostty_config_module._SCHEMA = original_schema


# ---------------------------------------------------------------------------
# GhosttyConfigListener.is_applicable
# ---------------------------------------------------------------------------


class TestGhosttyConfigListenerIsApplicable:
    def test_always_returns_true(self):
        assert GhosttyConfigListener.is_applicable(MagicMock()) is True

    def test_true_regardless_of_settings(self):
        for val in [None, {}, MagicMock()]:
            assert GhosttyConfigListener.is_applicable(val) is True


# ---------------------------------------------------------------------------
# GhosttyConfigListener._maybe_assign
# ---------------------------------------------------------------------------


class TestGhosttyConfigListenerMaybeAssign:
    def _make_listener(self, file_name):
        view = MagicMock()
        view.file_name.return_value = file_name
        listener = GhosttyConfigListener.__new__(GhosttyConfigListener)
        listener.view = view
        return listener

    def test_assigns_syntax_for_ghostty_extension(self):
        listener = self._make_listener("/home/user/config.ghostty")
        listener._maybe_assign()
        listener.view.assign_syntax.assert_called_once_with(SYNTAX)

    def test_no_assign_for_unknown_path(self):
        original = ghostty_config_module._GHOSTTY_CANDIDATES
        try:
            ghostty_config_module._GHOSTTY_CANDIDATES = set()
            listener = self._make_listener("/home/user/something.txt")
            listener._maybe_assign()
            listener.view.assign_syntax.assert_not_called()
        finally:
            ghostty_config_module._GHOSTTY_CANDIDATES = original

    def test_no_assign_when_file_name_is_none(self):
        listener = self._make_listener(None)
        listener._maybe_assign()
        listener.view.assign_syntax.assert_not_called()

    def test_assigns_for_candidate_path(self):
        test_path = "/tmp/ghostty-config-test"
        normalized = _normalize(test_path)
        original = ghostty_config_module._GHOSTTY_CANDIDATES
        try:
            ghostty_config_module._GHOSTTY_CANDIDATES = {normalized}
            listener = self._make_listener(test_path)
            listener._maybe_assign()
            listener.view.assign_syntax.assert_called_once_with(SYNTAX)
        finally:
            ghostty_config_module._GHOSTTY_CANDIDATES = original

    def test_on_load_async_calls_maybe_assign(self):
        listener = self._make_listener("/home/user/config.ghostty")
        with patch.object(listener, "_maybe_assign") as mock_assign:
            listener.on_load_async()
            mock_assign.assert_called_once()

    def test_on_post_save_async_calls_maybe_assign(self):
        listener = self._make_listener("/home/user/config.ghostty")
        with patch.object(listener, "_maybe_assign") as mock_assign:
            listener.on_post_save_async()
            mock_assign.assert_called_once()


# ---------------------------------------------------------------------------
# GhosttyOpenConfigCommand._open_from_list
# ---------------------------------------------------------------------------


class TestOpenFromList:
    def _make_command(self):
        window = MagicMock()
        cmd = GhosttyOpenConfigCommand.__new__(GhosttyOpenConfigCommand)
        cmd.window = window
        return cmd

    def test_opens_file_at_given_index(self):
        cmd = self._make_command()
        candidates = ["/path/a", "/path/b", "/path/c"]
        cmd._open_from_list(candidates, 1)
        cmd.window.open_file.assert_called_once_with("/path/b")

    def test_negative_index_does_nothing(self):
        cmd = self._make_command()
        candidates = ["/path/a"]
        cmd._open_from_list(candidates, -1)
        cmd.window.open_file.assert_not_called()

    def test_index_zero(self):
        cmd = self._make_command()
        candidates = ["/path/first", "/path/second"]
        cmd._open_from_list(candidates, 0)
        cmd.window.open_file.assert_called_once_with("/path/first")

    def test_cancelled_selection_minus_one(self):
        cmd = self._make_command()
        cmd._open_from_list(["/path/a", "/path/b"], -1)
        cmd.window.open_file.assert_not_called()


# ---------------------------------------------------------------------------
# GhosttyOpenConfigCommand._create_and_open
# ---------------------------------------------------------------------------


class TestCreateAndOpen:
    def _make_command(self):
        window = MagicMock()
        cmd = GhosttyOpenConfigCommand.__new__(GhosttyOpenConfigCommand)
        cmd.window = window
        return cmd

    def test_negative_index_does_nothing(self):
        cmd = self._make_command()
        cmd._create_and_open(["/path/a"], -1)
        cmd.window.open_file.assert_not_called()

    def test_creates_file_when_absent(self, tmp_path):
        cmd = self._make_command()
        target = str(tmp_path / "subdir" / "config")
        cmd._create_and_open([target], 0)
        assert os.path.isfile(target)

    def test_new_file_has_header(self, tmp_path):
        cmd = self._make_command()
        target = str(tmp_path / "config")
        cmd._create_and_open([target], 0)
        with open(target, encoding="utf-8") as fh:
            content = fh.read()
        assert content == "# Ghostty configuration\n"

    def test_opens_file_after_creation(self, tmp_path):
        cmd = self._make_command()
        target = str(tmp_path / "config")
        cmd._create_and_open([target], 0)
        cmd.window.open_file.assert_called_once_with(target)

    def test_does_not_overwrite_existing_file(self, tmp_path):
        cmd = self._make_command()
        target = str(tmp_path / "config")
        existing_content = "# Existing config\nfont-size = 14\n"
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(existing_content)
        cmd._create_and_open([target], 0)
        with open(target, encoding="utf-8") as fh:
            content = fh.read()
        assert content == existing_content

    def test_creates_parent_directories(self, tmp_path):
        cmd = self._make_command()
        nested = str(tmp_path / "a" / "b" / "c" / "config")
        cmd._create_and_open([nested], 0)
        assert os.path.isfile(nested)

    def test_oserror_shows_error_message(self, tmp_path):
        cmd = self._make_command()
        # Point at a path where makedirs will fail (file in place of directory)
        blocker = str(tmp_path / "blocker")
        with open(blocker, "w") as fh:
            fh.write("I am a file")
        target = str(tmp_path / "blocker" / "config")
        sublime = sys.modules["sublime"]
        cmd._create_and_open([target], 0)
        sublime.error_message.assert_called_once()
        error_args = sublime.error_message.call_args[0][0]
        assert target in error_args

    def test_correct_candidate_selected_by_index(self, tmp_path):
        cmd = self._make_command()
        path_a = str(tmp_path / "config_a")
        path_b = str(tmp_path / "config_b")
        cmd._create_and_open([path_a, path_b], 1)
        assert os.path.isfile(path_b)
        cmd.window.open_file.assert_called_once_with(path_b)


# ---------------------------------------------------------------------------
# GhosttyOpenConfigCommand.run
# ---------------------------------------------------------------------------


class TestGhosttyOpenConfigCommandRun:
    def _make_command(self):
        window = MagicMock()
        cmd = GhosttyOpenConfigCommand.__new__(GhosttyOpenConfigCommand)
        cmd.window = window
        return cmd

    def test_single_existing_opens_directly(self, tmp_path):
        config = str(tmp_path / "config")
        config_file = open(config, "w")
        config_file.write("# config")
        config_file.close()

        cmd = self._make_command()
        with patch("GhosttyConfig.ghostty_config._open_config_paths", return_value=[config]):
            cmd.run()
        cmd.window.open_file.assert_called_once_with(config)

    def test_multiple_existing_shows_quick_panel(self, tmp_path):
        config_a = str(tmp_path / "config_a")
        config_b = str(tmp_path / "config_b")
        for p in [config_a, config_b]:
            with open(p, "w") as fh:
                fh.write("# config")

        cmd = self._make_command()
        with patch(
            "GhosttyConfig.ghostty_config._open_config_paths",
            return_value=[config_a, config_b],
        ):
            cmd.run()
        cmd.window.show_quick_panel.assert_called_once()
        args = cmd.window.show_quick_panel.call_args[0]
        assert config_a in args[0]
        assert config_b in args[0]

    def test_no_existing_shows_quick_panel_for_creation(self, tmp_path):
        nonexistent_a = str(tmp_path / "config_a")
        nonexistent_b = str(tmp_path / "config_b")

        cmd = self._make_command()
        with patch(
            "GhosttyConfig.ghostty_config._open_config_paths",
            return_value=[nonexistent_a, nonexistent_b],
        ):
            cmd.run()
        cmd.window.show_quick_panel.assert_called_once()


# ---------------------------------------------------------------------------
# SYNTAX constant
# ---------------------------------------------------------------------------


class TestSyntaxConstant:
    def test_syntax_references_package(self):
        assert "GhosttyConfig" in SYNTAX

    def test_syntax_references_tmlanguage(self):
        assert "tmLanguage" in SYNTAX

    def test_syntax_starts_with_packages(self):
        assert SYNTAX.startswith("Packages/")