# Project Context for Claude

This file contains important context about the ChatGPT Browser project that should be preserved across Claude sessions.

## Project Overview

ChatGPT Browser is a simple, fast terminal-based tool for browsing and organizing ChatGPT and Claude conversation history. The codebase emphasizes simplicity and self-documenting code.

## Key Design Principles

1. **Simplicity First**: No unnecessary abstractions or complex inheritance
2. **Self-Documenting Code**: Clear names and obvious intent
3. **Minimal Dependencies**: Each module stands alone
4. **Direct Implementation**: Avoid over-engineering

## Project Structure

```
chatgpt_browser/
├── scripts/              # Entry points
│   ├── cgpt.py          # CLI entry point
│   └── cgpt-tui.py      # TUI entry point
├── src/
│   ├── core/            # Data models and loading
│   ├── tree/            # Tree organization logic
│   ├── tui/             # Terminal UI components
│   └── cli/             # Command line interface
├── tests/               # Test files
├── docs/                # Documentation
└── data/samples/        # Sample data
```

## Recent Updates

### Refactoring (2024)
The codebase was significantly refactored to improve modularity:
1. **Action Registration System**: Managers now register their actions with the TUI instead of having all logic in tui.py
2. **Modular Managers**: Separate managers for selection, search, operations, actions, and tree operations
3. **Reduced File Sizes**: TUI.py reduced from 1073 to 545 lines (49% reduction)

### Claude Support (2024)
Added support for browsing Claude Code conversation history:
1. **JSONL Format**: Claude stores conversations as JSONL files (one JSON object per line)
2. **Project Structure**: Conversations organized by project in `~/.claude/projects/<PROJECT_NAME>/`
3. **Auto-detection**: Format is automatically detected based on file extension or directory
4. **Unified Interface**: Both ChatGPT and Claude conversations use the same UI

## Key Components

### TUI Architecture
- `ActionHandler` base class for all managers
- `ActionContext` passes state between components
- `ActionResult` standardized return type
- Managers: SelectionManager, SearchManager, OperationsManager, ActionManager, TreeManager

### Data Loading
- `loader.py`: Auto-detects format and routes to appropriate loader
- `claude_loader.py`: Handles Claude JSONL format
- Unified `Conversation` and `Message` models for both formats

### Features
- Vim-like navigation (h/j/k/l, gg/G, etc.)
- Visual mode selection
- Tree organization with folders
- Search and filter functionality
- Undo/redo support
- Multi-select operations

## Testing

Run tests with: `pytest tests/test_simple.py -v`

All tests should pass before committing changes.

## Common Tasks

### Adding a New Keybinding
1. Add the key handling in `tree_view.py` `handle_input()` method
2. Return an action string (e.g., "new_action")
3. Add handler in appropriate manager's `can_handle()` and `handle()` methods
4. Update help text in `TreeManager.show_help()`

### Adding a New Manager
1. Create new file in `src/tui/` inheriting from `ActionHandler`
2. Implement `can_handle()` and `handle()` methods
3. Register in TUI's `run()` method in the `action_handlers` list

## Code Style

- No comments unless absolutely necessary
- Clear, descriptive names
- Keep methods short and focused
- Use type hints for clarity
- Follow existing patterns in the codebase

## Important Notes

- Function keys may not work in all terminals; alternative keys are provided
- The project uses curses for terminal UI
- No external dependencies beyond Python standard library
- Designed to work with ChatGPT's conversation export format