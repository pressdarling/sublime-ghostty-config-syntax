import json
import os
from typing import Any, Dict

_SCHEMA_CACHE: Dict[str, Any] | None = None


def schema_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "schema", "ghostty-config-syntax.schema.json")


def load_schema() -> Dict[str, Any]:
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is not None:
        return _SCHEMA_CACHE

    with open(schema_path(), "r", encoding="utf-8") as handle:
        _SCHEMA_CACHE = json.load(handle)
    return _SCHEMA_CACHE
