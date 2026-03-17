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
    return [parse_line(line, idx) for idx, line in enumerate(text.split("\n"))]


def parse_line(line: str, line_number: int) -> ParsedLine:
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
        value_start = equals_index + 1 + (len(after_equals) - len(after_equals.lstrip()))
        value_end = len(line.rstrip())

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
    equals_index = line.find("=")
    return equals_index == -1 or character <= equals_index


def is_in_value_position(line: str, character: int) -> bool:
    equals_index = line.find("=")
    return equals_index != -1 and character > equals_index
