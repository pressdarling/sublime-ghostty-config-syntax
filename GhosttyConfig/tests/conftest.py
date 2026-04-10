"""
Pytest configuration and shared fixtures for GhosttyConfig tests.

Provides mock implementations of the Sublime Text API (sublime and sublime_plugin
modules) so that plugin code can be imported and tested outside the Sublime Text
runtime environment.
"""
import sys
import types
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Mock sublime module
# ---------------------------------------------------------------------------

def _make_sublime_mock():
    """Build a minimal mock of the sublime module."""
    mod = types.ModuleType("sublime")

    INHIBIT_WORD_COMPLETIONS = 8

    class CompletionItem:
        """Minimal stand-in for sublime.CompletionItem."""

        def __init__(self, trigger, completion="", annotation="", details="", **kwargs):
            self.trigger = trigger
            self.completion = completion
            self.annotation = annotation
            self.details = details

        def __repr__(self):
            return (
                f"CompletionItem(trigger={self.trigger!r}, "
                f"completion={self.completion!r})"
            )

        def __eq__(self, other):
            if isinstance(other, CompletionItem):
                return (
                    self.trigger == other.trigger
                    and self.completion == other.completion
                )
            return NotImplemented

    class CompletionList:
        """Minimal stand-in for sublime.CompletionList."""

        def __init__(self, items, flags=0):
            self.items = items
            self.flags = flags

        def __repr__(self):
            return f"CompletionList({self.items!r}, flags={self.flags!r})"

    class Settings:
        """Minimal stand-in for sublime.Settings."""

        def __init__(self, data=None):
            self._data = data or {}

        def get(self, key, default=None):
            return self._data.get(key, default)

        def set(self, key, value):
            self._data[key] = value

    mod.INHIBIT_WORD_COMPLETIONS = INHIBIT_WORD_COMPLETIONS
    mod.CompletionItem = CompletionItem
    mod.CompletionList = CompletionList
    mod.Settings = Settings
    mod.load_settings = MagicMock(return_value=Settings())
    mod.error_message = MagicMock()
    return mod


def _make_sublime_plugin_mock():
    """Build a minimal mock of the sublime_plugin module."""
    mod = types.ModuleType("sublime_plugin")

    class ViewEventListener:
        """Minimal stand-in for sublime_plugin.ViewEventListener."""
        def __init__(self, view):
            self.view = view

    class WindowCommand:
        """Minimal stand-in for sublime_plugin.WindowCommand."""
        def __init__(self, window):
            self.window = window

    mod.ViewEventListener = ViewEventListener
    mod.WindowCommand = WindowCommand
    return mod


# Install mocks into sys.modules before any plugin code is imported.
sublime_mock = _make_sublime_mock()
sublime_plugin_mock = _make_sublime_plugin_mock()

sys.modules.setdefault("sublime", sublime_mock)
sys.modules.setdefault("sublime_plugin", sublime_plugin_mock)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sublime_mod():
    """Return the mock sublime module."""
    return sys.modules["sublime"]


@pytest.fixture()
def sublime_plugin_mod():
    """Return the mock sublime_plugin module."""
    return sys.modules["sublime_plugin"]


@pytest.fixture()
def minimal_schema():
    """Return a minimal schema dict sufficient for completion engine tests."""
    return {
        "options": {
            "font-size": {
                "type": "number",
                "description": "Font size in points.",
                "examples": ["12", "14", "16"],
            },
            "font-family": {
                "type": "string",
                "description": "Font family for regular text.",
                "repeatable": True,
                "examples": ["JetBrains Mono", "Fira Code"],
            },
            "background": {
                "type": "color",
                "description": "Background colour.",
                "examples": ["#282c34", "black"],
            },
            "cursor-style": {
                "type": "enum",
                "description": "Style of the cursor.",
                "enum": ["block", "bar", "underline", "block_hollow"],
                "examples": ["block", "bar"],
            },
            "cursor-style-blink": {
                "type": "boolean",
                "description": "Whether the cursor should blink.",
                "examples": ["true", "false"],
            },
            "keybind": {
                "type": "keybind",
                "description": "Keyboard binding.",
                "repeatable": True,
                "examples": ["ctrl+c=copy_to_clipboard"],
            },
            "theme": {
                "type": "string",
                "description": "Built-in theme name.",
                "examples": ["auto", "Catppuccin Mocha"],
            },
        },
        "repeatableKeys": ["font-family", "keybind", "palette"],
        "types": {
            "color": {
                "namedValues": ["black", "red", "green", "white"],
            },
            "keybind": {
                "modifiers": ["shift", "ctrl", "alt", "super"],
                "prefixes": ["global", "all", "unconsumed", "performable"],
            },
        },
    }