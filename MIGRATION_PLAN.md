# Ghostty VS Code → Sublime Text Migration Plan

This repository should be split into two layers:

1. **Reusable Ghostty domain logic** (grammar, schema, parsing, validation, key/value UX behavior)
2. **Editor host adapter** (Sublime plugin API and package metadata)

## File-by-file migration map

### Keep as source-of-truth (shared knowledge)
- `syntaxes/ghostty-config-syntax.tmLanguage.json`
- `schema/ghostty-config-syntax.schema.json`
- `src/parser/configParser.ts` (behavioral reference for Python port)
- `src/validation/validators.ts` (behavioral reference for Python validation parity)
- `src/providers/completionProvider.ts` (behavioral reference for completion parity)
- `src/commands/openConfig.ts` (behavioral reference for command parity)

### New Sublime package scaffold
- `GhosttyConfig/Ghostty Config.tmLanguage`
- `GhosttyConfig/schema/ghostty-config-syntax.schema.json`
- `GhosttyConfig/ghostty_config.py`
- `GhosttyConfig/lib/parser.py`
- `GhosttyConfig/lib/schema.py`
- `GhosttyConfig/lib/completion.py`
- `GhosttyConfig/Default.sublime-commands`
- `GhosttyConfig/Ghostty Config.sublime-settings`
- `GhosttyConfig/completions/Ghostty Config.sublime-completions`

## First pass deliverables in this branch

### 1) Syntax highlighting (ship immediately)
- Reuse the existing TextMate grammar as `Ghostty Config.tmLanguage`.
- Use path-based syntax assignment in plugin code for:
  - `~/.config/ghostty/config`
  - `~/Library/Application Support/com.mitchellh.ghostty/config`
  - `*.ghostty`

### 2) Parser port (Python)
- `GhosttyConfig/lib/parser.py`
  - Implements `parse_line()` and `parse_document()` with the same key/value and comment behavior as TS.
  - Preserves key and value ranges for feature consumers.
  - Exposes `is_in_key_position()` and `is_in_value_position()` for completion routing.

### 3) Completion port (Python + Sublime API)
- `GhosttyConfig/lib/completion.py`
  - Implements schema-aware key and value suggestions.
  - Routes by key vs value cursor position.
  - Includes type-driven value behavior for boolean/enum/color/keybind/example values.
- `GhosttyConfig/completions/Ghostty Config.sublime-completions`
  - Adds static baseline snippets for common keys.

### 4) Open-config command (WindowCommand)
- `GhosttyConfig/ghostty_config.py`
  - Adds `ghostty_open_config` command.
  - Opens existing config path if found.
  - Shows a quick panel when multiple paths exist.
  - Offers path selection and creates a default config file when absent.
- `GhosttyConfig/Default.sublime-commands`
  - Exposes the command in Command Palette.

## Follow-up milestones

1. Port validation logic to `GhosttyConfig/lib/validators.py` and surface errors with `add_regions()`.
2. Port hover provider behavior with `on_hover()` and minihtml popups.
3. Add syntax tests + package-level smoke checks.
4. Convert TextMate JSON grammar to `.sublime-syntax` when maintaining complex matching becomes painful.
5. Remove VS Code-specific packaging and runtime files once Sublime package reaches feature parity.
