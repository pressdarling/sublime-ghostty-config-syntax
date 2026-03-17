import json
import os
from typing import Any, Dict


SCHEMA_RELATIVE_PATH = os.path.join("schema", "ghostty-config-syntax.schema.json")


def load_schema(package_path: str) -> Dict[str, Any]:
    schema_path = os.path.join(package_path, SCHEMA_RELATIVE_PATH)
    with open(schema_path, "r", encoding="utf-8") as handle:
        return json.load(handle)
