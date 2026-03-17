import os
from dataclasses import dataclass
from typing import List


@dataclass
class ConfigLocation:
    path: str
    label: str
    exists: bool


def get_config_locations() -> List[ConfigLocation]:
    home = os.path.expanduser("~")
    xdg_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(home, ".config"))
    xdg_path = os.path.join(xdg_home, "ghostty", "config")

    locations = [ConfigLocation(path=xdg_path, label=f"XDG: {xdg_path}", exists=os.path.exists(xdg_path))]

    macos_path = os.path.join(home, "Library", "Application Support", "com.mitchellh.ghostty", "config")
    locations.append(ConfigLocation(path=macos_path, label=f"macOS: {macos_path}", exists=os.path.exists(macos_path)))

    return locations


def ensure_parent(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def write_default_config(path: str) -> None:
    ensure_parent(path)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(
            "# Ghostty Configuration\n"
            "# See https://ghostty.org/docs/config/reference for all options\n\n"
            "# font-family = \"JetBrains Mono\"\n"
            "# font-size = 14\n"
            "# theme = auto\n"
            "# keybind = ctrl+shift+c=copy_to_clipboard\n"
        )


def is_ghostty_config_path(path: str | None) -> bool:
    if not path:
        return False
    return any(os.path.normpath(path) == os.path.normpath(loc.path) for loc in get_config_locations()) or path.endswith(".ghostty")
