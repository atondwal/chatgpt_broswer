# ChatGPT History Tree Organization Design Document

## Current Context
- Existing ChatGPT browser: 630+ conversations, 13,809+ messages
- Modular architecture: `ConversationLoader`, `ConversationSearcher`, `ChatGPTBrowserCLI`
- Professional TUI with multiple view modes and real-time search
- **Problem**: Flat conversation list becomes unwieldy at scale
- **Goal**: Add Firefox Tree Style Tabs-inspired organization with folders, tags, and custom metadata

## Requirements

### Core Features
- **Tree Organization**: Hierarchical folders like Firefox Tree Style Tabs
- **Metadata**: Tags, notes, custom titles for conversations
- **TUI Integration**: Tree view mode in existing interface
- **Persistence**: JSON auxiliary file alongside conversations.json
- **Search**: Filter within organized structure

### Quality Goals
- **Performance**: < 100ms load time, supports 10,000+ conversations
- **Reliability**: Atomic file operations, backup/recovery
- **Compatibility**: Zero impact on existing functionality

## Key Design Decisions

1. **JSON Storage**: Human-readable auxiliary file using existing Conversation UUIDs
2. **Adjacency List + Materialized Paths**: Efficient tree operations with fast queries
3. **TUI Extension**: Add new ViewMode.CONVERSATION_TREE to existing architecture
4. **Atomic Operations**: Backup/recovery for data safety

## Technical Design

### Core Architecture

```python
class ConversationOrganizer:
    """Main orchestrator integrating tree management with existing conversation data"""
    def load_organization(self) -> OrganizationData
    def save_organization(self) -> None
    def get_organized_conversations(self) -> List[Tuple[TreeNode, Conversation]]

class TreeManager:
    """Adjacency list + materialized paths for efficient tree operations"""
    def create_folder(self, name: str, parent_id: Optional[str] = None) -> str
    def move_node(self, node_id: str, new_parent_id: Optional[str]) -> None
    def get_tree_order(self) -> List[TreeNode]  # Depth-first for rendering

class MetadataStore:
    """JSON persistence with atomic writes and backup/recovery"""
    def load(self) -> OrganizationData
    def save(self, data: OrganizationData) -> None
```

### Data Models

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Set

class NodeType(Enum):
    FOLDER = "folder"
    CONVERSATION = "conversation"

@dataclass
class TreeNode:
    id: str                    # UUID for folders, conversation_id for conversations
    name: str                  # Display name
    node_type: NodeType        # FOLDER or CONVERSATION
    parent_id: Optional[str] = None   # Parent node ID
    children: Set[str] = field(default_factory=set)  # Child node IDs
    path: str = ""             # Materialized path: "/Work/Python/"
    expanded: bool = True      # UI state

@dataclass
class ConversationMetadata:
    conversation_id: str       # Links to Conversation.id
    custom_title: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    notes: str = ""
    favorite: bool = False

@dataclass
class OrganizationData:
    tree_nodes: Dict[str, TreeNode] = field(default_factory=dict)
    conversation_metadata: Dict[str, ConversationMetadata] = field(default_factory=dict)
    root_nodes: Set[str] = field(default_factory=set)  # Top-level folder IDs
    version: str = "1.0"       # Schema version for migration
```

### Integration Points

- **CLI**: Add `organize` command to `ChatGPTBrowserCLI`
- **TUI**: Add `CONVERSATION_TREE` mode and `TreeListView` component
- **Storage**: `conversations_organization.json` alongside existing file
- **Data**: Reference existing `Conversation.id` UUIDs
- **Compatibility**: Zero impact on existing functionality

## Implementation Plan

### Phase 1: Core Tree System
- **File**: `conversation_tree.py`
- Data models: `TreeNode`, `ConversationMetadata`, `OrganizationData`
- `TreeManager`: create/move/delete operations with cycle detection
- `MetadataStore`: atomic JSON persistence with backup
- Unit tests with 95%+ coverage

### Phase 2: CLI Integration  
- Extend `chatgpt_browser.py` with `ConversationOrganizer`
- Add `organize` subcommand: create folders, move conversations, manage tags
- File path resolution for `conversations_organization.json`
- Migration tool for existing conversations

### Phase 3: TUI Tree View
- Extend `chatgpt_tui.py` with `CONVERSATION_TREE` mode
- `TreeListView` component with Unicode rendering (`├─`, `└─`)
- Keyboard navigation: expand/collapse, move between folders
- Integrate with existing search and detail views

### Phase 4: Advanced Features
- Bulk operations and drag-drop style commands
- Advanced search within tree structure
- Import/export organization templates

## Testing Strategy

### Unit Tests
- **TreeManager**: folder creation, node moving, cycle detection, path calculation
- **MetadataStore**: JSON persistence, atomic writes, corruption recovery
- **Data Models**: serialization, validation, defaults

### Integration Tests  
- CLI organize commands with real conversation data
- TUI tree navigation with mock curses
- File operations: atomic writes, backup/restore
- Performance: 10,000+ conversations, 1,000+ folders

### Performance Targets
- Load organization: < 100ms
- Tree rendering: < 50ms
- File saves: < 50ms with atomic guarantees


## Future Enhancements

- **AI Organization**: Auto-categorize conversations by content
- **Templates**: Import/export common folder structures  
- **External Sync**: Integration with Obsidian, Notion
- **Advanced Search**: Full-text search within tree structure
- **Collaboration**: Multi-user organization support

## Known Limitations

- Large trees (>1000 folders) may impact TUI performance
- JSON format limits scale (could migrate to SQLite for huge datasets)
- No undo/redo for organization changes
- No real-time collaboration

## Security & Dependencies

### Security
- Auxiliary file contains only UUIDs and user metadata (no ChatGPT content)
- File permissions: 0600 (user read/write only)
- Input validation for folder names and tags
- Atomic file operations prevent corruption

### Dependencies
- **Runtime**: Python 3.8+, standard library only
- **Development**: pytest, mypy, black for code quality

## Success Metrics

- **Performance**: Tree operations < 100ms, file saves < 50ms
- **Quality**: 95%+ test coverage, zero critical bugs  
- **Usability**: Seamless upgrade for existing users
- **Adoption**: Tree view becomes preferred mode for large conversation sets

## References
- Firefox Tree Style Tabs: https://github.com/piroor/treestyletab
- Adjacency List vs Nested Sets: https://stackoverflow.com/questions/889788
- ChatGPT Export Format: OpenAI conversation export schema
- Related design patterns: Composite Pattern, Repository Pattern