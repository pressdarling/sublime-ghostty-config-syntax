import re
from typing import Dict, List, Optional, TypedDict


class Range(TypedDict):
    start: int
    end: int


class ParsedLine(TypedDict, total=False):
    type: str
    line_number: int
    key: str
    value: str
    key_range: Range
    value_range: Range
    raw: str


KEY_VALUE_REGEX = re.compile(r"^(\s*)([a-zA-Z][a-zA-Z0-9_-]*)\s*=\s*(.*?)\s*$")
COMMENT_REGEX = re.compile(r"^\s*#")


def parse_document(text: str) -> List[ParsedLine]:
    return [parse_line(line, number) for number, line in enumerate(text.splitlines())]


def parse_line(line: str, line_number: int) -> ParsedLine:
    if line.strip() == "":
        return {"type": "empty", "line_number": line_number, "raw": line}

    if COMMENT_REGEX.search(line):
        return {"type": "comment", "line_number": line_number, "raw": line}

    match = KEY_VALUE_REGEX.search(line)
    if match:
        indent, key, value = match.groups()
        key_start = len(indent)
        key_end = key_start + len(key)
        equals_index = line.find("=")
        value_slice = line[equals_index + 1 :]
        value_start = equals_index + 1 + (len(value_slice) - len(value_slice.lstrip()))
        value_end = len(line.rstrip())

        return {
            "type": "keyValue",
            "line_number": line_number,
            "key": key,
            "value": value.strip(),
            "key_range": {"start": key_start, "end": key_end},
            "value_range": {"start": value_start, "end": value_end},
            "raw": line,
        }

    return {"type": "invalid", "line_number": line_number, "raw": line}


def is_in_key_position(line: str, character: int) -> bool:
    equals_index = line.find("=")
    return equals_index == -1 or character <= equals_index


def is_in_value_position(line: str, character: int) -> bool:
    equals_index = line.find("=")
    return equals_index != -1 and character > equals_index


def key_at_position(line: str, row: int, col: int) -> Optional[str]:
    parsed = parse_line(line, row)
    key_range = parsed.get("key_range")
    if parsed.get("type") != "keyValue" or not key_range:
        return None

    if key_range["start"] <= col <= key_range["end"]:
        return parsed.get("key")

    return None
