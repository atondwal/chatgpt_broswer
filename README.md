# ChatGPT History Browser

A simple, fast tool for browsing and organizing your ChatGPT conversation history with excellent UX.

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

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/chatgpt_browser.git
cd chatgpt_browser

# Option 1: Use directly with Python
python scripts/cgpt-tui.py conversations.json

# Option 2: Install in development mode
pip install -e .
cgpt-tui conversations.json

# Option 3: Use make commands
make run  # Runs the TUI with conversations.json
```

### Running the TUI

```bash
# Direct execution
python scripts/cgpt-tui.py conversations.json

# After installation
cgpt-tui conversations.json

# Using make
make run
```

### Running the CLI

```bash
# Direct execution
python scripts/cgpt.py conversations.json list
python scripts/cgpt.py conversations.json search "python"
python scripts/cgpt.py conversations.json export 1

# After installation
cgpt conversations.json list
cgpt conversations.json search "python"
cgpt conversations.json export 1
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
- **↑/↓**: Scroll
- **Page Up/Down**: Page scroll
- **q**: Back to list

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
chatgpt_browser/
├── scripts/              # Entry point scripts
│   ├── cgpt.py          # CLI entry point
│   └── cgpt-tui.py      # TUI entry point
├── src/                 # Source code
│   ├── core/            # Core data models and loading
│   ├── tree/            # Tree organization logic
│   ├── tui/             # Terminal UI components
│   └── cli/             # Command line interface
├── tests/               # Test files
├── docs/                # Documentation
├── data/samples/        # Sample data files
├── Makefile            # Development commands
├── pyproject.toml      # Python package configuration
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

### Make Commands

```bash
make help       # Show available commands
make install    # Install in development mode
make test       # Run all tests
make clean      # Clean cache and temp files
make run        # Run the TUI with conversations.json
```

### Testing

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_simple.py -v
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

**A simple tool that does one thing well: browse ChatGPT conversations.**