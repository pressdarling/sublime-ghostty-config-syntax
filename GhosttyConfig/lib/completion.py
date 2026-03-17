import sublime
from .parser import is_in_key_position, is_in_value_position, parse_line


class GhosttyCompletionEngine:
    def __init__(self, schema):
        self.schema = schema

    def completions_for(self, line_text: str, cursor_col: int):
        text_before_cursor = line_text[:cursor_col]
        if text_before_cursor.strip().startswith("#"):
            return []

        if is_in_key_position(line_text, cursor_col):
            return self._key_completions(text_before_cursor)

        if is_in_value_position(line_text, cursor_col):
            parsed = parse_line(line_text, 0)
            if parsed.key:
                return self._value_completions(parsed.key, text_before_cursor)

        return []

    def _key_completions(self, text_before_cursor: str):
        prefix = text_before_cursor.strip().lower()
        items = []
        for key, option in self.schema.get("options", {}).items():
            if prefix and prefix not in key.lower():
                continue
            details = option.get("type", "string")
            if option.get("repeatable"):
                details += " (repeatable)"
            items.append(
                sublime.CompletionItem(
                    trigger=key,
                    completion=f"{key} = ",
                    annotation=details,
                    details=option.get("description", ""),
                )
            )
        return items

    def _value_completions(self, key: str, text_before_cursor: str):
        option = self.schema.get("options", {}).get(key)
        if not option:
            return []

        equals_index = text_before_cursor.find("=")
        partial = (
            text_before_cursor[equals_index + 1 :].strip().lower()
            if equals_index != -1
            else ""
        )

        option_type = option.get("type")
        if option_type == "boolean":
            values = ["true", "false"]
        elif option_type == "enum":
            values = option.get("enum", [])
        elif option_type == "color":
            values = ["#", "black", "white", "transparent", "cell-foreground", "cell-background"]
        elif option_type == "keybind":
            values = ["ctrl+", "shift+", "alt+", "super+", "clear"]
        else:
            values = option.get("examples", [])

        return [
            sublime.CompletionItem(trigger=v, completion=v)
            for v in values
            if not partial or partial in v.lower()
        ]
