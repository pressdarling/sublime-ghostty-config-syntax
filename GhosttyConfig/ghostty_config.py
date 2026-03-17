import os

import sublime
import sublime_plugin

from lib.completion import GhosttyCompletionEngine
from lib.schema import load_schema

PACKAGE_PATH = os.path.dirname(__file__)
SYNTAX = "Packages/GhosttyConfig/Ghostty Config.tmLanguage"


def _normalize(path):
    return os.path.normcase(os.path.normpath(path))


def _ghostty_candidates():
    home = os.path.expanduser("~")
    return {
        _normalize(os.path.join(home, ".config", "ghostty", "config")),
        _normalize(
            os.path.join(
                home,
                "Library",
                "Application Support",
                "com.mitchellh.ghostty",
                "config",
            )
        ),
    }


def is_ghostty_config_path(path: str) -> bool:
    if not path:
        return False
    normalized = _normalize(path)
    return normalized in _ghostty_candidates() or normalized.endswith(".ghostty")


_SCHEMA = None
_COMPLETIONS = None


def plugin_loaded():
    global _SCHEMA, _COMPLETIONS
    _SCHEMA = load_schema(PACKAGE_PATH)
    _COMPLETIONS = GhosttyCompletionEngine(_SCHEMA)


class GhosttyConfigListener(sublime_plugin.ViewEventListener):
    @classmethod
    def is_applicable(cls, settings):
        return True

    def on_load_async(self):
        self._maybe_assign()

    def on_post_save_async(self):
        self._maybe_assign()

    def _maybe_assign(self):
        path = self.view.file_name()
        if path and is_ghostty_config_path(path):
            self.view.assign_syntax(SYNTAX)

    def on_query_completions(self, prefix, locations):
        if not locations or _COMPLETIONS is None:
            return None

        point = locations[0]
        row, col = self.view.rowcol(point)
        line_region = self.view.line(point)
        line_text = self.view.substr(line_region)
        items = _COMPLETIONS.completions_for(line_text, col)
        if not items:
            return None
        return sublime.CompletionList(items, sublime.INHIBIT_WORD_COMPLETIONS)


class GhosttyOpenConfigCommand(sublime_plugin.WindowCommand):
    def run(self):
        candidates = [
            os.path.expanduser("~/.config/ghostty/config"),
            os.path.expanduser("~/Library/Application Support/com.mitchellh.ghostty/config"),
        ]
        existing = [p for p in candidates if os.path.exists(p)]

        if len(existing) == 1:
            self.window.open_file(existing[0])
            return

        if len(existing) > 1:
            self.window.show_quick_panel(existing, lambda idx: self._open_from_list(existing, idx))
            return

        self.window.show_quick_panel(candidates, lambda idx: self._create_and_open(candidates, idx))

    def _open_from_list(self, candidates, idx):
        if idx >= 0:
            self.window.open_file(candidates[idx])

    def _create_and_open(self, candidates, idx):
        if idx < 0:
            return
        target = candidates[idx]
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if not os.path.exists(target):
            with open(target, "w", encoding="utf-8") as handle:
                handle.write("# Ghostty configuration\n")
        self.window.open_file(target)
