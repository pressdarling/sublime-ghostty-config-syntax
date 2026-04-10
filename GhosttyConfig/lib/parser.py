import re
from dataclasses import dataclass
from typing import Optional

KEY_VALUE_REGEX = re.compile(r"^(\s*)([a-zA-Z][a-zA-Z0-9_-]*)\s*=\s*(.*?)\s*$")
COMMENT_REGEX = re.compile(r"^\s*#")


@dataclass
class Range:
    start: int
    end: int


@dataclass
class ParsedLine:
    type: str
    line_number: int
    raw: str
    key: Optional[str] = None
    value: Optional[str] = None
    key_range: Optional[Range] = None
    value_range: Optional[Range] = None


def parse_document(text: str):
    """
    Parse a configuration document into a list of per-line ParsedLine records.
    
    Parameters:
        text (str): The full configuration document as a single string.
    
    Returns:
        list[ParsedLine]: A list of ParsedLine objects, one per original line in `text`, in order.
    """
    return [parse_line(line, idx) for idx, line in enumerate(text.split("\n"))]


def parse_line(line: str, line_number: int) -> ParsedLine:
    """
    Parse a single line of configuration text and return a ParsedLine describing its classification and extracted components.
    
    The line is classified as one of:
    - "empty": line contains only whitespace.
    - "comment": line starts with optional whitespace followed by `#`.
    - "keyValue": line matches a `key = value` pattern; `key` is returned (string), `value` is returned with surrounding whitespace trimmed, `key_range` gives the character start/end of the key, and `value_range` gives the character start/end of the value (the start is the character immediately after `=` plus any following whitespace; the end is the index corresponding to the line with trailing whitespace removed).
    - "invalid": line does not match any recognised pattern.
    
    Parameters:
        line (str): The raw text of the line to parse.
        line_number (int): Zero-based index of the line within the document.
    
    Returns:
        ParsedLine: A dataclass instance with `type`, `line_number`, `raw` always set; for `keyValue` lines `key`, `value`, `key_range` and `value_range` are also populated.
    """
    if line.strip() == "":
        return ParsedLine(type="empty", line_number=line_number, raw=line)

    if COMMENT_REGEX.match(line):
        return ParsedLine(type="comment", line_number=line_number, raw=line)

    match = KEY_VALUE_REGEX.match(line)
    if match:
        indent, key, value = match.groups()
        key_start = len(indent)
        key_end = key_start + len(key)

        equals_index = line.find("=")
        after_equals = line[equals_index + 1 :]
        leading_ws = len(after_equals) - len(after_equals.lstrip())
        value_start = equals_index + 1 + leading_ws
        value_end = max(value_start, len(line.rstrip()))

        return ParsedLine(
            type="keyValue",
            line_number=line_number,
            key=key,
            value=value.strip(),
            key_range=Range(start=key_start, end=key_end),
            value_range=Range(start=value_start, end=value_end),
            raw=line,
        )

    return ParsedLine(type="invalid", line_number=line_number, raw=line)


def is_in_key_position(line: str, character: int) -> bool:
    """
    Determine whether a character index lies within the key portion of a line (before or at the first '=').
    
    Parameters:
    	line (str): The raw line to inspect.
    	character (int): Zero-based character index to test.
    
    Returns:
    	`True` if the line contains no '=' or `character` is less than or equal to the index of the first '='; `False` otherwise.
    """
    equals_index = line.find("=")
    return equals_index == -1 or character <= equals_index


def is_in_value_position(line: str, character: int) -> bool:
    """
    Determine whether a character index is within the value portion of a key/value line.
    
    Parameters:
    	line (str): The line to inspect.
    	character (int): Zero-based character index within the line.
    
    Returns:
    	True if the line contains an '=' and `character` is greater than the index of the first '='; False otherwise.
    """
    equals_index = line.find("=")
    return equals_index != -1 and character > equals_index
