import os

import sublime
import sublime_plugin

from GhosttyConfig.lib.completion import GhosttyCompletionEngine
from GhosttyConfig.lib.schema import load_schema

PACKAGE_PATH = os.path.dirname(__file__)
SETTINGS_FILE = "Ghostty Config.sublime-settings"
SYNTAX = "Packages/GhosttyConfig/Ghostty Config.tmLanguage"


def _normalize(path: str) -> str:
    """
    Produce a canonicalised filesystem path suitable for OS-aware comparisons.
    
    Parameters:
    	path (str): A filesystem path.
    
    Returns:
    	normalised_path (str): The input path with redundant separators and up-level references collapsed and case adjusted according to the current operating system.
    """
    return os.path.normcase(os.path.normpath(path))


def _open_config_paths() -> list[str]:
    """
    Return configured Ghostty configuration candidate paths expanded for the current environment.
    
    Filters the `ghostty_open_config_paths` setting to non-empty string entries, expands any leading `~` in each path, and appends the Windows `%APPDATA%\ghostty\config` path when `APPDATA` is set and that path is not already present.
    
    Returns:
        list[str]: Filesystem paths from the setting (with `~` expanded) plus the optional Windows APPDATA candidate; empty list if the setting is missing or not a list.
    """
    settings = sublime.load_settings(SETTINGS_FILE)
    paths = settings.get("ghostty_open_config_paths", [])
    if not isinstance(paths, list):
        return []
    expanded = [os.path.expanduser(path) for path in paths if isinstance(path, str) and path]
    appdata = os.environ.get("APPDATA")
    if appdata:
        windows_path = os.path.join(appdata, "ghostty", "config")
        if windows_path not in expanded:
            expanded.append(windows_path)
    return expanded


def _ghostty_candidates() -> set[str]:
    """
    Return a set of filesystem paths considered candidate Ghostty configuration files.
    
    Returns:
        candidates (set[str]): Normalised paths derived from the `ghostty_open_config_paths` setting.
    """
    return {_normalize(path) for path in _open_config_paths()}


def is_ghostty_config_path(path: str) -> bool:
    """
    Determine whether a filesystem path refers to a Ghostty configuration file.
    
    Returns:
        `True` if the normalized path matches a configured Ghostty candidate or ends with `.ghostty`, `False` otherwise.
    """
    if not path:
        return False
    normalized = _normalize(path)
    return normalized in _GHOSTTY_CANDIDATES or normalized.endswith(".ghostty")


_SCHEMA = None
_COMPLETIONS = None
_GHOSTTY_CANDIDATES = set()


def plugin_loaded():
    """
    Initialise module-wide Ghostty schema, completion engine and candidate paths.
    
    Loads the Ghostty schema from the package path and constructs the completion
    engine and the set of known Ghostty configuration candidate paths. If schema
    loading fails the schema is set to an empty dict and an error message is printed.
    The function updates the module globals `_SCHEMA`, `_COMPLETIONS` and
    `_GHOSTTY_CANDIDATES`.
    """
    global _SCHEMA, _COMPLETIONS, _GHOSTTY_CANDIDATES
    try:
        _SCHEMA = load_schema(PACKAGE_PATH)
    except Exception as exc:
        print(f"[GhosttyConfig] Failed to load schema: {exc}")
        _SCHEMA = {}
    _COMPLETIONS = GhosttyCompletionEngine(_SCHEMA)
    _GHOSTTY_CANDIDATES = _ghostty_candidates()


class GhosttyConfigListener(sublime_plugin.ViewEventListener):
    @classmethod
    def is_applicable(cls, settings: sublime.Settings) -> bool:
        """
        Indicates the listener is applicable for every view so load/save hooks can assign Ghostty syntax by file path.
        
        @returns
            `true` if the listener should be active for the view (always `true`).
        """
        _ = settings
        # Keep listener active so load/save hooks can assign Ghostty syntax by path.
        return True

    def on_load_async(self):
        """
        Handle the view load event and assign Ghostty syntax when the file is a Ghostty configuration.
        
        Called after a view finishes loading; if the view's file path identifies it as a Ghostty config, the Ghostty syntax is applied to the view.
        """
        self._maybe_assign()

    def on_post_save_async(self):
        """
        Re-evaluates the view's file path after it is saved and assigns Ghostty syntax if the file is recognised as a Ghostty configuration.
        """
        self._maybe_assign()

    def _maybe_assign(self) -> None:
        """
        Assign Ghostty syntax to the view when its file path corresponds to a recognised Ghostty configuration.
        
        If the view has an associated file and is_ghostty_config_path(path) returns True for that file, assigns the SYNTAX value to the view.
        """
        path = self.view.file_name()
        if path and is_ghostty_config_path(path):
            self.view.assign_syntax(SYNTAX)

    def on_query_completions(self, prefix: str, locations: list[int]):
        """
        Provide completion suggestions for the current view when editing Ghostty configuration files.
        
        Checks the view's syntax or file path to ensure Ghostty context, computes the current line and cursor column from `locations`, and returns completions produced by the global completion engine.
        
        Parameters:
        	prefix (str): The current completion prefix (ignored by this implementation).
        	locations (list[int]): List of buffer positions for the completion request; the first position is used to determine the cursor column.
        
        Returns:
        	sublime.CompletionList | None: A CompletionList with completion items and word completions inhibited, or `None` if completions are not applicable or none are available.
        """
        _ = prefix
        if not locations or _COMPLETIONS is None:
            return None

        syntax = self.view.settings().get("syntax") or ""
        path = self.view.file_name()
        if not ((syntax == SYNTAX or "ghostty" in syntax.lower()) or (path and is_ghostty_config_path(path))):
            return None

        point = locations[0]
        _, col = self.view.rowcol(point)
        line_region = self.view.line(point)
        line_text = self.view.substr(line_region)
        items = _COMPLETIONS.completions_for(line_text, col)
        if not items:
            return None
        return sublime.CompletionList(items, sublime.INHIBIT_WORD_COMPLETIONS)


class GhosttyOpenConfigCommand(sublime_plugin.WindowCommand):
    def run(self) -> None:
        """
        Open or create a Ghostty configuration file from the configured candidate paths.
        
        If exactly one candidate exists, open it directly. If multiple exist, show a quick panel to choose one to open. If none exist, show a quick panel to choose a target to create (ensuring parent directories are created) and then open it.
        """
        candidates = _open_config_paths()
        existing = [path for path in candidates if os.path.exists(path)]

        if len(existing) == 1:
            self.window.open_file(existing[0])
            return

        if len(existing) > 1:
            self.window.show_quick_panel(existing, lambda idx: self._open_from_list(existing, idx))
            return

        self.window.show_quick_panel(candidates, lambda idx: self._create_and_open(candidates, idx))

    def _open_from_list(self, candidates: list[str], idx: int) -> None:
        """
        Open the candidate file at the given index in the current window.
        
        Parameters:
            candidates (list[str]): Ordered list of file paths to open.
            idx (int): Selected index into `candidates`. If less than 0 the selection is treated as cancelled and nothing happens.
        """
        if idx >= 0:
            self.window.open_file(candidates[idx])

    def _create_and_open(self, candidates: list[str], idx: int) -> None:
        """
        Create the selected candidate file (if missing) and open it in the window.
        
        If `idx` is negative the function does nothing. It ensures the target's parent
        directories exist, writes a header line "# Ghostty configuration\n" when creating
        a new file, and opens the file in the current window. On filesystem errors an
        error dialog is shown.
        
        Parameters:
            candidates (list[str]): List of candidate file paths.
            idx (int): Index of the candidate to create/open.
        """
        if idx < 0:
            return
        target = candidates[idx]
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            if not os.path.exists(target):
                with open(target, "w", encoding="utf-8") as handle:
                    handle.write("# Ghostty configuration\n")
            self.window.open_file(target)
        except OSError as exc:
            sublime.error_message(f"Failed to create Ghostty config at {target}: {exc}")
