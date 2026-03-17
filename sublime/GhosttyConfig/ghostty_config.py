from __future__ import annotations

import sublime
import sublime_plugin

from lib.completion import CompletionEngine
from lib.paths import get_config_locations, is_ghostty_config_path, write_default_config
from lib.schema import load_schema

SYNTAX = "Packages/GhosttyConfig/syntaxes/ghostty-config-syntax.tmLanguage.json"


class GhosttyConfigEventListener(sublime_plugin.ViewEventListener):
    @classmethod
    def is_applicable(cls, settings):
        return True

    def on_load_async(self):
        self._assign_syntax_if_needed()

    def on_post_save_async(self):
        self._assign_syntax_if_needed()

    def _assign_syntax_if_needed(self):
        filename = self.view.file_name()
        if filename and is_ghostty_config_path(filename):
            self.view.assign_syntax(SYNTAX)


class GhosttyConfigCompletions(sublime_plugin.ViewEventListener):
    @classmethod
    def is_applicable(cls, settings):
        return True

    def on_query_completions(self, prefix, locations):
        if self.view.syntax() is None or "ghostty" not in self.view.syntax().scope:
            return None

        row, col = self.view.rowcol(locations[0])
        line = self.view.substr(self.view.line(locations[0]))

        engine = CompletionEngine(load_schema())
        items = engine.completions_for_line(line, col)
        return sublime.CompletionList(items, sublime.INHIBIT_WORD_COMPLETIONS)


class GhosttyOpenConfigCommand(sublime_plugin.WindowCommand):
    def run(self):
        locations = get_config_locations()
        existing = [loc for loc in locations if loc.exists]

        if len(existing) == 1:
            self.window.open_file(existing[0].path)
            return

        if len(existing) > 1:
            self.window.show_quick_panel([loc.label for loc in existing], lambda idx: self._open_existing(idx, existing))
            return

        preferred = locations[0]
        if sublime.ok_cancel_dialog(f"No Ghostty config found. Create one at\n{preferred.path}?", "Create"):
            write_default_config(preferred.path)
            self.window.open_file(preferred.path)

    def _open_existing(self, idx, existing):
        if idx >= 0:
            self.window.open_file(existing[idx].path)
