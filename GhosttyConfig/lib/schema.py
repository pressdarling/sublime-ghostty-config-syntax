import json
import logging
import os
from typing import Any

LOGGER = logging.getLogger(__name__)

SCHEMA_RELATIVE_PATH = os.path.join("schema", "ghostty-config-syntax.schema.json")


def load_schema(package_path: str) -> dict[str, Any]:
    schema_path = os.path.join(package_path, SCHEMA_RELATIVE_PATH)
    try:
        with open(schema_path, encoding="utf-8") as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.error("Failed to load Ghostty schema at %s: %s", schema_path, exc)
        return {}
