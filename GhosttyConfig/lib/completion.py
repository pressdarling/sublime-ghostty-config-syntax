import sublime
from .parser import is_in_key_position, is_in_value_position, parse_line


class GhosttyCompletionEngine:
    def __init__(self, schema) -> None:
        """
        Initialise the completion engine with the configuration schema used to generate completion items.
        
        Parameters:
            schema (dict): Schema defining available configuration options and metadata. Expected keys include:
                - "options": mapping of option names to their metadata (type, description, examples, repeatable, enum, etc.).
                - "repeatableKeys": list of keys treated as repeatable.
                - "types": optional type-specific data (for example, a "color" type with "namedValues").
        """
        self.schema = schema

    def completions_for(self, line_text: str, cursor_col: int):
        """
        Provide Sublime Text completion items for a configuration line at a given cursor column.
        
        Parameters:
            line_text (str): The full text of the current line.
            cursor_col (int): The cursor column index within `line_text` (0-based).
        
        Returns:
            list: A list of `sublime.CompletionItem` objects for the current key or value context; an empty list when the line is a comment, the cursor is not in a key/value position, or the key is not recognised.
        """
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
        """
        Generate completion items for configuration keys based on the text immediately before the cursor.
        
        Parameters:
            text_before_cursor (str): The substring of the current line up to the cursor; used to derive a lowercase prefix for filtering available keys.
        
        Returns:
            list: A list of sublime.CompletionItem objects for matching schema keys. Each item triggers the key and inserts "<key> = " as the completion, with the annotation set to the option's type (appending " (repeatable)" when applicable) and details set to the option's description.
        """
        prefix = text_before_cursor.strip().lower()
        items = []
        repeatable_keys = set(self.schema.get("repeatableKeys", []))
        for key, option in self.schema.get("options", {}).items():
            if prefix and prefix not in key.lower():
                continue
            details = option.get("type", "string")
            if option.get("repeatable") or key in repeatable_keys:
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
        """
        Produce completion items for possible values of a configuration `key` using the engine's schema and the text before the cursor.
        
        Candidates are selected from the schema according to the option's type (boolean, enum, colour names or '#', keybind modifiers/prefixes or 'clear', or example values) and filtered by any partial value found after the first '=' in `text_before_cursor`.
        
        Parameters:
            key (str): The configuration key whose values are being completed.
            text_before_cursor (str): The line text up to the cursor position; used to derive a partial value after '='.
        
        Returns:
            list: A list of sublime.CompletionItem objects for matching value candidates; returns an empty list if the key is not present in the schema or no candidates match.
        """
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
            color_type_info = self.schema.get("types", {}).get("color", {})
            values = ["#"] + color_type_info.get("namedValues", [])
        elif option_type == "keybind":
            keybind_type_info = self.schema.get("types", {}).get("keybind", {})
            modifiers = [f"{modifier}+" for modifier in keybind_type_info.get("modifiers", [])]
            prefixes = [f"{prefix}:" for prefix in keybind_type_info.get("prefixes", [])]
            values = modifiers + prefixes + ["clear"]
        else:
            values = option.get("examples", [])

        return [
            sublime.CompletionItem(trigger=v, completion=v)
            for v in values
            if not partial or partial in v.lower()
        ]
