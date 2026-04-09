import os

import sublime
import sublime_plugin

from GhosttyConfig.lib.completion import GhosttyCompletionEngine
from GhosttyConfig.lib.schema import load_schema

PACKAGE_PATH = os.path.dirname(__file__)
SETTINGS_FILE = "Ghostty Config.sublime-settings"
SYNTAX = "Packages/GhosttyConfig/Ghostty Config.tmLanguage"


def _normalize(path: str) -> str:
    return os.path.normcase(os.path.normpath(path))


def _open_config_paths() -> list[str]:
    settings = sublime.load_settings(SETTINGS_FILE)
    paths = settings.get("ghostty_open_config_paths", [])
    if not isinstance(paths, list):
        return []
    expanded = [os.path.expanduser(path) for path in paths if isinstance(path, str) and path]
    appdata = os.environ.get("APPDATA")
    if appdata:
        windows_path = os.path.join(appdata, "ghostty", "config")
        if windows_path not in expanded:
            expanded.append(windows_path)
    return expanded


def _ghostty_candidates() -> set[str]:
    return {_normalize(path) for path in _open_config_paths()}


def is_ghostty_config_path(path: str) -> bool:
    if not path:
        return False
    normalized = _normalize(path)
    return normalized in _GHOSTTY_CANDIDATES or normalized.endswith(".ghostty")


_SCHEMA = None
_COMPLETIONS = None
_GHOSTTY_CANDIDATES = set()


def plugin_loaded():
    global _SCHEMA, _COMPLETIONS, _GHOSTTY_CANDIDATES
    try:
        _SCHEMA = load_schema(PACKAGE_PATH)
    except Exception as exc:
        print(f"[GhosttyConfig] Failed to load schema: {exc}")
        _SCHEMA = {}
    _COMPLETIONS = GhosttyCompletionEngine(_SCHEMA)
    _GHOSTTY_CANDIDATES = _ghostty_candidates()


class GhosttyConfigListener(sublime_plugin.ViewEventListener):
    @classmethod
    def is_applicable(cls, settings: sublime.Settings) -> bool:
        _ = settings
        # Keep listener active so load/save hooks can assign Ghostty syntax by path.
        return True

    def on_load_async(self):
        self._maybe_assign()

    def on_post_save_async(self):
        self._maybe_assign()

    def _maybe_assign(self) -> None:
        path = self.view.file_name()
        if path and is_ghostty_config_path(path):
            self.view.assign_syntax(SYNTAX)

    def on_query_completions(self, prefix: str, locations: list[int]):
        _ = prefix
        if not locations or _COMPLETIONS is None:
            return None

        syntax = self.view.settings().get("syntax") or ""
        path = self.view.file_name()
        if not ((syntax == SYNTAX or "ghostty" in syntax.lower()) or (path and is_ghostty_config_path(path))):
            return None

        point = locations[0]
        _, col = self.view.rowcol(point)
        line_region = self.view.line(point)
        line_text = self.view.substr(line_region)
        items = _COMPLETIONS.completions_for(line_text, col)
        if not items:
            return None
        return sublime.CompletionList(items, sublime.INHIBIT_WORD_COMPLETIONS)


class GhosttyOpenConfigCommand(sublime_plugin.WindowCommand):
    def run(self) -> None:
        candidates = _open_config_paths()
        existing = [path for path in candidates if os.path.exists(path)]

        if len(existing) == 1:
            self.window.open_file(existing[0])
            return

        if len(existing) > 1:
            self.window.show_quick_panel(existing, lambda idx: self._open_from_list(existing, idx))
            return

        self.window.show_quick_panel(candidates, lambda idx: self._create_and_open(candidates, idx))

    def _open_from_list(self, candidates: list[str], idx: int) -> None:
        if idx >= 0:
            self.window.open_file(candidates[idx])

    def _create_and_open(self, candidates: list[str], idx: int) -> None:
        if idx < 0:
            return
        target = candidates[idx]
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            if not os.path.exists(target):
                with open(target, "w", encoding="utf-8") as handle:
                    handle.write("# Ghostty configuration\n")
            self.window.open_file(target)
        except OSError as exc:
            sublime.error_message(f"Failed to create Ghostty config at {target}: {exc}")
