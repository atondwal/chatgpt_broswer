# ChatGPT History Browser

A simple, fast tool for browsing and organizing your ChatGPT conversation history.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Lines](https://img.shields.io/badge/lines-1367-brightgreen.svg)

## ✨ Features

- **Interactive Terminal UI**: Browse conversations with a responsive interface
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

### Run the TUI

```bash
# Clone and run
git clone https://github.com/your-username/chatgpt_browser.git
cd chatgpt_browser
./cgpt-tui.py conversations.json
```

### Run the CLI

```bash
# List conversations
./cgpt.py conversations.json list

# Search
./cgpt.py conversations.json search "python"

# Export a conversation
./cgpt.py conversations.json export 1
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

### Tree Organization
- **n**: New folder
- **r**: Rename
- **d**: Delete
- **m**: Move
- **Space**: Toggle folder

### Reading Conversations
- **↑/↓**: Scroll
- **Page Up/Down**: Page scroll
- **q**: Back to list

## 🏗️ Architecture: Self-Documenting Code

This codebase demonstrates **self-documenting code** principles. The code is simple, direct, and tells its own story without excessive comments or documentation.

### The Simplified Structure

```
src/
├── core/
│   ├── models.py           # Data structures
│   └── simple_loader.py    # Load conversations (179 lines)
├── tree/
│   └── simple_tree.py      # Folder organization (205 lines)
├── tui/
│   ├── enhanced_tui.py     # Main TUI app (399 lines)
│   ├── simple_detail.py    # Conversation viewer (119 lines)
│   ├── simple_search.py    # Search interface (109 lines)
│   └── simple_input.py     # Input dialogs (158 lines)
└── cli/
    └── simple_cli.py       # Command line interface (126 lines)
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

## 🧪 Testing

```bash
# Run tests
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