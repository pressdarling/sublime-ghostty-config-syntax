# Sublime Text Migration Plan (File-by-File)

This repository is being split into two layers:

1. **Reusable Ghostty domain model** (grammar, schema, parser/validation logic)
2. **Editor adapter** (Sublime Text Python plugin + resource files)

## Phase 1: Ship Syntax + Command Skeleton

### Keep and reuse
- `syntaxes/ghostty-config-syntax.tmLanguage.json`
- `schema/ghostty-config-syntax.schema.json`

### Add Sublime package scaffold
- `sublime/GhosttyConfig/syntaxes/ghostty-config-syntax.tmLanguage.json`
  - copied grammar for immediate highlighting support.
- `sublime/GhosttyConfig/Default.sublime-commands`
  - command palette entry for opening Ghostty config.
- `sublime/GhosttyConfig/Ghostty Config.sublime-settings`
  - package-local settings toggles.
- `sublime/GhosttyConfig/ghostty_config.py`
  - plugin entry point (listeners + `ghostty_open_config` command).
- `sublime/GhosttyConfig/completions/Ghostty Config.sublime-completions`
  - safe static completions.

## Phase 2: Port the runtime logic to Python

### Parser port
- `sublime/GhosttyConfig/lib/parser.py`
  - first-pass translation of `src/parser/configParser.ts`.
  - exports line/document parsing and key/value position checks.

### Schema loading
- `sublime/GhosttyConfig/lib/schema.py`
  - lazy, cached schema loading for plugin features.

### Completion engine port
- `sublime/GhosttyConfig/lib/completion.py`
  - first-pass translation of `src/providers/completionProvider.ts`.
  - preserves key-vs-value behavior, type-aware value suggestions, and key docs.

### Open-config command port
- `sublime/GhosttyConfig/lib/paths.py`
  - Ghostty config location detection and default config creation.
- `sublime/GhosttyConfig/ghostty_config.py`
  - `GhosttyOpenConfigCommand` uses quick-panel/create flows mirroring VS Code behavior.

## Phase 3: Continue feature parity

### Next files to add
- `sublime/GhosttyConfig/lib/validators.py` (port from `src/validation/validators.ts`)
- `sublime/GhosttyConfig/lib/diagnostics.py` (map validation output to `view.add_regions` + status)
- `sublime/GhosttyConfig/lib/hover.py` (port markdown docs to MiniHTML popups)

### Tests and packaging
- Add syntax tests:
  - `sublime/GhosttyConfig/tests/syntax_test_ghostty_config.ghostty`
- Add unit tests for Python parser/completion/path modules under:
  - `sublime/GhosttyConfig/tests/`
- Keep existing TS tests as regression reference until full migration completes.

## Legacy VS Code files to retire after parity

When the Sublime package reaches parity, remove VS Code runtime/marketplace plumbing:

- `src/extension.ts`
- `src/providers/*`
- `src/commands/*`
- VS Code-specific fields in `package.json` (`engines.vscode`, `main`, `activationEvents`, `contributes`, publisher/marketplace metadata)

Keep schema/grammar assets editor-neutral for dual-use by future adapters.
