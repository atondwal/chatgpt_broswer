# CCSM (Claude Code Session Manager)

A simple, fast tool for browsing and organizing your Claude Code and ChatGPT conversation history with excellent UX.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Lines](https://img.shields.io/badge/lines-1500-brightgreen.svg)

## ✨ Features

- **Interactive Terminal UI**: Browse conversations with a responsive interface
- **Enhanced Tree View**: Visual hierarchy with guide lines and vim-like navigation
- **Search**: Find conversations by title or content
- **Folder Organization**: Create folders and organize conversations
- **Conversation Viewer**: Read messages with proper formatting
- **Command Line Tools**: CLI for automation and scripting

## 🚀 Quick Start

### Get Your ChatGPT Data

1. Go to [ChatGPT](https://chat.openai.com)
2. Click your profile → **Settings** → **Data controls**
3. Click **Export data** and download the zip file
4. Extract `conversations.json` from the zip

### Browse Claude Code History

Claude Code automatically saves your conversations locally in `~/.claude/projects/`. No export needed!

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/ccsm.git
cd ccsm

# Option 1: Use directly with Python (no installation needed)
python scripts/ccsm-tui.py conversations.json

# Option 2: Install for convenient access from anywhere
pip install -e .
ccsm-tui conversations.json
```

### Running the TUI

#### For ChatGPT History
```bash
# Direct execution (no installation needed)
python scripts/ccsm-tui.py conversations.json

# After installation
ccsm-tui conversations.json
```

#### For Claude Code History
```bash
# List available Claude projects
python scripts/ccsm.py projects

# Browse a specific Claude project
python scripts/ccsm-tui.py ~/.claude/projects/<PROJECT_NAME>

# Or use the shortcut
python scripts/ccsm-tui.py --claude-project <PROJECT_NAME>
```

### Running the CLI

```bash
# List conversations (matches claude --resume format)
python scripts/ccsm.py conversations.json list
# Output:
#      Modified     Created      # Messages  Summary
# ❯  1. 10h ago     1 day ago          133 This session is being continued from...
#    2. 1 day ago   1 day ago          607 Refactoring TUI: Breaking Down...
#    3. 2 days ago  2 days ago          281 CCSM: Tree Org, TUI...

# Search conversations
python scripts/ccsm.py conversations.json search "python"

# Export a specific conversation
python scripts/ccsm.py conversations.json export 1

# List Claude projects
python scripts/ccsm.py projects
# Output:
#      Last Modified   # Convos   Project Name
# ❯  1. Just now              20  home/atondwal/playground
#    2. 2 days ago             1  home/atondwal
```

## 🎮 TUI Controls

### Navigation
- **↑/↓**: Navigate
- **Enter**: View conversation
- **t**: Tree view
- **l**: List view
- **q**: Quit

### Search
- **/**: Start search
- **Type**: Filter as you type
- **Enter**: Apply
- **ESC**: Cancel

### Tree View (Enhanced!)
- **Navigation**:
  - **↑/↓** or **j/k**: Move through items
  - **g/G**: Jump to top/bottom
  - **h**: Jump to parent folder
  - **l**: Expand folder or enter conversation
- **Actions**:
  - **Space**: Toggle folder expand/collapse
  - **Enter**: Open conversation or toggle folder
  - **\***: Expand all folders
  - **-**: Collapse all folders
- **Organization**:
  - **n**: Create new folder
  - **r**: Rename item
  - **d**: Delete item
  - **m**: Move item to another folder
- **?**: Show help with all commands

### Reading Conversations
- **Enter**: Opens conversation in `less` for fast incremental viewing
- **e**: Opens conversation in your `$EDITOR` (vim, nano, etc.) for full editing
- Conversations are formatted as Markdown for syntax highlighting
- `less` provides instant viewing with search, scrolling, and navigation

## 🌳 Enhanced Tree View Features

The tree view provides an excellent user experience with:

- **Visual Hierarchy**: Tree guide lines (│, ├─, └─) show structure clearly
- **Smart Icons**: 
  - Folders show expand state (▶ collapsed, ▼ expanded)
  - Child count displayed for each folder
  - 💬 for conversations, 📁 for folders
- **Vim-style Navigation**: Use h/j/k/l for efficient keyboard control
- **Bulk Operations**: Expand/collapse all folders with * and -
- **Contextual Help**: Press ? anytime to see available commands
- **Full-width Selection**: Clear visual feedback for selected items

## 🏗️ Architecture: Self-Documenting Code

This codebase demonstrates **self-documenting code** principles. The code is simple, direct, and tells its own story without excessive comments or documentation.

### Project Structure

```
ccsm/
├── scripts/              # Entry point scripts
│   ├── ccsm.py          # CLI entry point
│   └── ccsm-tui.py      # TUI entry point
├── src/                 # Source code
│   ├── core/            # Core data models and loading
│   ├── tree/            # Tree organization logic
│   ├── tui/             # Terminal UI components
│   └── cli/             # Command line interface
├── tests/               # Test files
├── docs/                # Additional documentation
├── data/samples/        # Sample data files
├── pyproject.toml      # Python package configuration
├── pytest.ini          # Test configuration
├── conftest.py         # Test setup
└── README.md           # This file
```

### Code That Tells Its Own Story

Each module is self-contained and obvious in purpose:

```python
# From simple_tree.py
class TreeNode:
    """A node in the tree - either a folder or conversation."""
    def __init__(self, id: str, name: str, is_folder: bool, parent_id: Optional[str] = None):
        self.id = id
        self.name = name
        self.is_folder = is_folder
        self.parent_id = parent_id
        self.children: Set[str] = set()
        self.expanded = True
```

```python
# From simple_loader.py
def load_conversations(file_path: str) -> List[Conversation]:
    """Load conversations from ChatGPT export file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle wrapped format
    if isinstance(data, dict) and 'conversations' in data:
        data = data['conversations']
    
    # ... simple, direct parsing logic
```

### Key Principles

1. **No Unnecessary Abstractions**: Direct implementations without complex inheritance
2. **Clear Names**: Functions and variables that explain themselves
3. **Simple Data Flow**: Easy to follow from input to output
4. **Minimal Dependencies**: Each module stands alone
5. **Obvious Intent**: You can understand what code does by reading it

### Stats

- **Total Lines**: 1,367 (down from 7,900)
- **Longest File**: 399 lines (enhanced_tui.py)
- **No Base Classes**: Zero abstract interfaces
- **No Complex Inheritance**: Direct, simple classes

## 🛠️ Development

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_simple.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

### Cleaning Up

```bash
# Remove Python cache files
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
```

The tests are also self-documenting:

```python
def test_load_basic_conversation(self):
    """Test loading a basic conversation."""
    test_data = [{
        'id': 'test-1',
        'title': 'Test Conversation',
        'create_time': 1234567890,
        'messages': [
            {'id': 'msg1', 'role': 'user', 'content': 'Hello'},
            {'id': 'msg2', 'role': 'assistant', 'content': 'Hi there!'}
        ]
    }]
    # ... clear test logic
```

## 📝 License

MIT License - see LICENSE file for details.

---

**A simple tool that does one thing well: browse Claude Code and ChatGPT conversations.**