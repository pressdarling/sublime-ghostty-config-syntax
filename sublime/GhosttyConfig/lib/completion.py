from __future__ import annotations

from typing import Any, Dict, List

import sublime

from .parser import is_in_key_position, is_in_value_position, parse_line


class CompletionEngine:
    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema

    def completions_for_line(self, line: str, caret_col: int) -> List[sublime.CompletionItem]:
        before_cursor = line[:caret_col]
        if before_cursor.strip().startswith("#"):
            return []

        if is_in_key_position(line, caret_col):
            return self._key_completions(before_cursor)

        if is_in_value_position(line, caret_col):
            parsed = parse_line(line, 0)
            key = parsed.get("key")
            if key:
                return self._value_completions(key, before_cursor)

        return []

    def _key_completions(self, before_cursor: str) -> List[sublime.CompletionItem]:
        prefix = before_cursor.strip().lower()
        items: List[sublime.CompletionItem] = []

        for key, option in self.schema.get("options", {}).items():
            if prefix and prefix not in key.lower():
                continue

            annotation = option.get("type", "")
            details = self._key_details(key, option)
            items.append(
                sublime.CompletionItem(
                    trigger=key,
                    completion=f"{key} = $0",
                    completion_format=sublime.COMPLETION_FORMAT_SNIPPET,
                    kind=sublime.KIND_VARIABLE,
                    annotation=annotation,
                    details=details,
                )
            )

        return items

    def _value_completions(self, key: str, before_cursor: str) -> List[sublime.CompletionItem]:
        option = self.schema.get("options", {}).get(key)
        if not option:
            return []

        equals_index = before_cursor.find("=")
        partial = before_cursor[equals_index + 1 :].strip().lower() if equals_index != -1 else ""
        value_type = option.get("type")

        if value_type == "boolean":
            return self._simple_values(["true", "false"], "Boolean", partial)
        if value_type == "enum":
            return self._simple_values(option.get("enum", []), "Enum", partial)
        if value_type == "color":
            values = ["#RRGGBB", "black", "white", "transparent", "cell-background", "cell-foreground"]
            return self._simple_values(values, "Colour", partial)
        if value_type == "theme":
            values = ["auto", "light", "dark", "Catppuccin Mocha", "Dracula"]
            return self._simple_values(values, "Theme", partial)
        if value_type == "keybind":
            return self._keybind_values(partial)

        return self._simple_values(option.get("examples", []), "Example", partial)

    def _simple_values(self, values: List[str], annotation: str, partial: str) -> List[sublime.CompletionItem]:
        return [
            sublime.CompletionItem(
                trigger=value,
                completion=value,
                kind=sublime.KIND_VALUE,
                annotation=annotation,
            )
            for value in values
            if not partial or partial in value.lower()
        ]

    def _keybind_values(self, partial: str) -> List[sublime.CompletionItem]:
        values = [
            "ctrl+shift+c=copy_to_clipboard",
            "ctrl+shift+v=paste_from_clipboard",
            "ctrl+t=new_tab",
            "clear",
            "global:",
        ]
        return self._simple_values(values, "Keybind", partial)

    def _key_details(self, key: str, option: Dict[str, Any]) -> str:
        parts = [f"<b>{key}</b>", option.get("description", "")]
        if option.get("enum"):
            parts.append("Values: " + ", ".join(option["enum"]))
        if option.get("examples"):
            parts.append("Examples: " + ", ".join(option["examples"]))
        return "<br>".join(p for p in parts if p)
