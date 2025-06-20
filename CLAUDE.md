# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ChatGPT Browser is a simple, fast terminal-based tool for browsing and organizing ChatGPT and Claude conversation history. The codebase emphasizes simplicity and self-documenting code.

## Development Commands

### Terminal Cleanup
```bash
# Fix terminal after bad curses exit
python -c "import curses; curses.endwin()" 2>/dev/null || echo "Attempted terminal cleanup"
```

### Testing
```bash
# Run all tests
pytest tests/test_simple.py -v

# Run specific test
pytest tests/test_simple.py::TestSimpleLoader::test_load_basic_conversation -v

# Run tests by marker
pytest -m unit        # Unit tests only
pytest -m integration # Integration tests
pytest -m tui        # TUI-specific tests
```

### Code Formatting
```bash
# Format code with Black (line-length: 120)
black src/ scripts/ tests/

# Sort imports
isort src/ scripts/ tests/
```

### Installation for Development
```bash
# Install in development mode
pip install -e .

# Entry points available after installation
cgpt      # CLI interface
cgpt-tui  # Terminal UI interface
```

## Key Design Principles

1. **Simplicity First**: No unnecessary abstractions or complex inheritance
2. **Self-Documenting Code**: Clear names and obvious intent
3. **Minimal Dependencies**: Each module stands alone (no external dependencies beyond Python standard library)
4. **Direct Implementation**: Avoid over-engineering

## Architecture Overview

The codebase was significantly simplified from 7,900 lines to ~1,500 lines while improving modularity:

### Project Structure
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

### TUI Architecture (Action-Based System)
The TUI uses a modular action-based architecture:

1. **Base Classes**:
   - `ActionHandler`: Base class for all managers
   - `ActionContext`: Passes state between components
   - `ActionResult`: Standardized return type

2. **Managers** (each handles specific concerns):
   - `SelectionManager`: Visual mode and multi-select operations
   - `SearchManager`: Search and filter functionality
   - `OperationsManager`: CRUD operations on conversations
   - `ActionManager`: Undo/redo/copy/paste functionality
   - `TreeManager`: Tree navigation and help display

3. **Action Flow**:
   - `tree_view.py` handles input and returns action strings
   - TUI dispatches actions to appropriate managers
   - Managers update state and return results

### Data Format Support

1. **ChatGPT Format**: JSON export from ChatGPT
2. **Claude Format**: JSONL files in `~/.claude/projects/<PROJECT_NAME>/`
3. **Auto-detection**: Format detected by file extension or directory structure
4. **Unified Model**: Both formats use same `Conversation` and `Message` models

## Common Development Tasks

### Adding a New Keybinding
1. Add key handling in `tree_view.py` `handle_input()` method
2. Return an action string (e.g., "new_action")
3. Add handler in appropriate manager's `can_handle()` and `handle()` methods
4. Update help text in `TreeManager.show_help()`

### Adding a New Manager
1. Create new file in `src/tui/` inheriting from `ActionHandler`
2. Implement `can_handle()` and `handle()` methods
3. Register in TUI's `run()` method in the `action_handlers` list

### Testing Changes
- Always run `pytest tests/test_simple.py -v` before committing
- Add tests for new functionality in appropriate test files
- Use temporary files for test isolation

## Code Style Guidelines

- No comments unless absolutely necessary
- Clear, descriptive names
- Keep methods under 50 lines
- Use type hints for clarity
- Follow existing patterns in the codebase
- Format with Black (line-length: 120)
- Sort imports with isort

## Important Notes

- Function keys may not work in all terminals; alternative keys are provided
- The project uses curses for terminal UI
- No external dependencies beyond Python standard library
- Designed to work with ChatGPT's conversation export format
- Claude support requires `claude_loader.py` (currently missing in some test scenarios)

## Recent Updates

### Modular Refactoring (2024)
- Reduced TUI.py from 1073 to 545 lines (49% reduction)
- Action registration system allows managers to self-register
- Improved separation of concerns

### Claude Support (2024)
- Added JSONL format support for Claude Code conversations
- Project-based organization in `~/.claude/projects/`
- Unified interface for both ChatGPT and Claude formats

## Development Workflow

- After every change, test and commit. If you're on a feature branch, see if you need to merge in master and fix anything.