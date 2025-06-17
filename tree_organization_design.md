# ChatGPT History Tree Organization Design Document

## Current Context
- Existing ChatGPT history browser with 630+ conversations, 13,809+ messages
- Architecture: Modular design with `ConversationLoader`, `ConversationSearcher`, `ConversationExporter`, `ChatGPTBrowserCLI`
- Current flat conversation list view in TUI (`chatgpt_tui.py`) with `ViewMode` enum system
- Professional curses-based interface with `ConversationListView`, `ConversationDetailView`, `SearchView`, `HelpView`
- Basic search and filtering capabilities with real-time filtering
- Existing data models: `Conversation` (with UUID), `Message`, `MessageRole`, `ContentType`
- Path handling: `~/.chatgpt/conversations.json` default with `--path` override support
- No user-defined organization or categorization system
- Pain points: difficult to navigate large conversation lists, no way to group related conversations, no custom metadata or notes

## Requirements

### Functional Requirements
- Tree-style hierarchical organization similar to Firefox's Tree Style Tabs
- User-defined folders/categories with drag-drop style organization
- Auxiliary metadata storage (tags, notes, custom titles, folders)
- UUID-based referencing to ChatGPT conversations
- Import/export of organization structure
- Search within organized structure
- Visual tree representation in TUI with expand/collapse
- Persistence of organization data across sessions

### Non-Functional Requirements
- Fast loading of organization data (< 100ms for 1000+ conversations)
- Minimal memory footprint for tree structure
- Backward compatibility with existing conversation data
- Atomic updates to prevent data corruption
- Support for 10,000+ conversations with nested folders
- Cross-platform file format (JSON-based)

## Design Decisions

### 1. Auxiliary Metadata Storage Format
Will implement JSON-based auxiliary file because:
- Human-readable and editable
- Standard library support (no external dependencies)
- Easy backup/version control integration
- Supports complex nested structures
- Trade-offs: Slightly larger than binary formats, but negligible for this use case

### 2. UUID Reference Strategy
Will use ChatGPT conversation UUIDs as primary keys because:
- Stable across file moves/renames
- Already present in ChatGPT export format
- Avoids fragility of filename-based references
- Enables robust data integrity checks
- Alternative considered: file paths (rejected due to fragility)

### 3. Tree Structure Implementation
Will implement adjacency list model with materialized path because:
- Efficient tree queries and operations
- Simple move/reorganization operations
- Fast parent/child relationship lookups
- Supports arbitrary nesting depth
- Alternative considered: nested sets (rejected due to complexity for user modifications)

## Technical Design

### 1. Core Components
```python
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import uuid
import shutil
import tempfile
from datetime import datetime

class ConversationOrganizer:
    """Main orchestrator for tree organization functionality"""
    def __init__(self, aux_file_path: Path, conversations: List[Conversation]):
        self.aux_file_path = aux_file_path
        self.conversations = {conv.id: conv for conv in conversations}
        self.tree_manager = TreeManager()
        self.metadata_store = MetadataStore(aux_file_path)
        self.organization_data: Optional[OrganizationData] = None
    
    def load_organization(self) -> OrganizationData:
        """Load organization from auxiliary file"""
        self.organization_data = self.metadata_store.load()
        self.tree_manager.load_from_data(self.organization_data)
        return self.organization_data
    
    def save_organization(self) -> None:
        """Save organization to auxiliary file"""
        if self.organization_data:
            self.organization_data.update_modified_time()
            self.metadata_store.save(self.organization_data)
    
    def get_organized_conversations(self) -> List[Tuple[TreeNode, Optional[Conversation]]]:
        """Get conversations organized by tree structure"""
        result = []
        for node in self.tree_manager.get_tree_order():
            conversation = None
            if node.is_conversation():
                conversation = self.conversations.get(node.id)
            result.append((node, conversation))
        return result
    
    def search_in_tree(self, search_term: str, include_content: bool = False) -> List[TreeNode]:
        """Search within the organized tree structure"""
        return self.tree_manager.search_nodes(search_term, include_content)

class TreeManager:
    """Manages hierarchical tree structure operations with adjacency list + materialized paths"""
    def __init__(self):
        self.nodes: Dict[str, TreeNode] = {}
        self.root_nodes: Set[str] = set()
        self.path_cache: Dict[str, str] = {}  # node_id -> materialized_path
    
    def create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """Create new folder node and return its ID"""
        folder_id = str(uuid.uuid4())
        
        # Validate parent exists
        if parent_id and parent_id not in self.nodes:
            raise ValueError(f"Parent node {parent_id} does not exist")
        
        # Create folder node
        folder = TreeNode(
            id=folder_id,
            name=name,
            node_type=NodeType.FOLDER,
            parent_id=parent_id
        )
        
        # Add to tree structure
        self.nodes[folder_id] = folder
        
        if parent_id:
            self.nodes[parent_id].children.add(folder_id)
        else:
            self.root_nodes.add(folder_id)
        
        # Update materialized path
        self._update_path(folder_id)
        
        return folder_id
    
    def move_node(self, node_id: str, new_parent_id: Optional[str]) -> None:
        """Move node to new parent, updating all paths"""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} does not exist")
        
        # Prevent cycles
        if new_parent_id and self._would_create_cycle(node_id, new_parent_id):
            raise ValueError("Cannot move node: would create cycle")
        
        node = self.nodes[node_id]
        old_parent_id = node.parent_id
        
        # Remove from old parent
        if old_parent_id:
            self.nodes[old_parent_id].children.discard(node_id)
        else:
            self.root_nodes.discard(node_id)
        
        # Add to new parent
        node.parent_id = new_parent_id
        if new_parent_id:
            self.nodes[new_parent_id].children.add(node_id)
        else:
            self.root_nodes.add(node_id)
        
        # Update paths for this node and all descendants
        self._update_path_recursive(node_id)
    
    def get_tree_order(self) -> List[TreeNode]:
        """Get all nodes in tree display order (depth-first)"""
        result = []
        for root_id in sorted(self.root_nodes, key=lambda x: self.nodes[x].order):
            self._collect_tree_order(root_id, result, 0)
        return result
    
    def _collect_tree_order(self, node_id: str, result: List[TreeNode], depth: int) -> None:
        """Recursively collect nodes in tree order"""
        node = self.nodes[node_id]
        node.depth = depth  # Add depth for rendering
        result.append(node)
        
        if node.expanded and node.children:
            for child_id in sorted(node.children, key=lambda x: self.nodes[x].order):
                self._collect_tree_order(child_id, result, depth + 1)
    
    def _update_path(self, node_id: str) -> None:
        """Update materialized path for a single node"""
        node = self.nodes[node_id]
        if node.parent_id:
            parent_path = self.path_cache.get(node.parent_id, "")
            node.path = f"{parent_path}{node.name}/"
        else:
            node.path = f"/{node.name}/"
        
        self.path_cache[node_id] = node.path
    
    def _would_create_cycle(self, node_id: str, potential_parent_id: str) -> bool:
        """Check if moving node would create a cycle"""
        current = potential_parent_id
        visited = set()
        
        while current and current not in visited:
            if current == node_id:
                return True
            visited.add(current)
            current = self.nodes[current].parent_id
        
        return False

class MetadataStore:
    """Manages JSON persistence with atomic writes and backup/recovery"""
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.backup_path = file_path.with_suffix('.json.backup')
    
    def load(self) -> OrganizationData:
        """Load organization data with corruption recovery"""
        # Try main file first
        if self.file_path.exists():
            try:
                return self._load_from_file(self.file_path)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logging.warning(f"Corrupted organization file, trying backup: {e}")
        
        # Try backup file
        if self.backup_path.exists():
            try:
                return self._load_from_file(self.backup_path)
            except Exception as e:
                logging.error(f"Backup file also corrupted: {e}")
        
        # Return empty organization
        return OrganizationData()
    
    def save(self, data: OrganizationData) -> None:
        """Save with atomic write and backup"""
        # Create backup of existing file
        if self.file_path.exists():
            shutil.copy2(self.file_path, self.backup_path)
        
        # Atomic write using temporary file
        with tempfile.NamedTemporaryFile(
            mode='w', 
            dir=self.file_path.parent,
            delete=False,
            suffix='.tmp'
        ) as tmp_file:
            json.dump(self._serialize_data(data), tmp_file, indent=2)
            tmp_path = Path(tmp_file.name)
        
        # Atomic move
        tmp_path.replace(self.file_path)
        
        # Set restrictive permissions
        self.file_path.chmod(0o600)
```

### 2. Data Models
```python
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

class NodeType(Enum):
    """Types of nodes in the organization tree"""
    FOLDER = "folder"
    CONVERSATION = "conversation"

@dataclass
class TreeNode:
    """Represents a node in the organization tree"""
    id: str  # UUID for folders, conversation ID for conversations
    name: str  # Display name (folder name or custom conversation title)
    node_type: NodeType
    parent_id: Optional[str] = None
    children: Set[str] = field(default_factory=set)
    path: str = ""  # Materialized path: "/Work/Python Projects/"
    expanded: bool = True  # UI state for tree rendering
    order: int = 0  # Sort order within parent
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def is_conversation(self) -> bool:
        return self.node_type == NodeType.CONVERSATION
    
    def is_folder(self) -> bool:
        return self.node_type == NodeType.FOLDER

@dataclass
class ConversationMetadata:
    """Extended metadata for conversations"""
    conversation_id: str  # References existing Conversation.id
    custom_title: Optional[str] = None  # Overrides original title
    tags: Set[str] = field(default_factory=set)  # User-defined tags
    notes: str = ""  # User notes
    color: Optional[str] = None  # Hex color for visual categorization
    favorite: bool = False
    archived: bool = False
    priority: int = 0  # 0=normal, 1=high, -1=low
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def get_display_title(self, original_title: str) -> str:
        """Get title to display (custom or original)"""
        return self.custom_title if self.custom_title else original_title

@dataclass
class OrganizationData:
    """Root data structure for auxiliary file"""
    version: str = "1.0"
    tree_nodes: Dict[str, TreeNode] = field(default_factory=dict)
    conversation_metadata: Dict[str, ConversationMetadata] = field(default_factory=dict)
    root_nodes: Set[str] = field(default_factory=set)  # Top-level node IDs
    ui_state: Dict[str, any] = field(default_factory=dict)  # Expanded state, etc.
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def update_modified_time(self) -> None:
        """Update the modification timestamp"""
        self.modified_at = datetime.utcnow().isoformat()
```

### 3. Integration Points
- **CLI Integration**: Extends `ChatGPTBrowserCLI` with new `organize` command and `--tree` flag for TUI
- **TUI Integration**: Adds `TREE_VIEW` to existing `ViewMode` enum, creates `TreeView` component
- **Data Integration**: Uses existing `Conversation.id` (UUID) for tree node references
- **File Storage**: Auxiliary file stored as `{conversations_file_stem}_organization.json` using existing path resolution
- **Search Integration**: Extends `ConversationSearcher` to work with tree-filtered results
- **Backward Compatibility**: All existing CLI commands continue to work unchanged

```python
# CLI Integration Example
class ChatGPTBrowserCLI:
    def cmd_organize(self) -> None:
        """Launch organization management interface"""
        organizer = ConversationOrganizer(self._get_organization_path())
        # ... organization commands
    
    def cmd_tui(self, tree_mode: bool = False) -> None:
        """Launch TUI with optional tree view"""
        tui = ChatGPTTUI(
            conversations_path=str(self.conversations_path),
            tree_mode=tree_mode,
            debug=self.debug
        )

# TUI Integration Example  
class ViewMode(Enum):
    CONVERSATION_LIST = "list"
    CONVERSATION_TREE = "tree"  # New tree view mode
    CONVERSATION_DETAIL = "detail"
    SEARCH = "search"
    HELP = "help"
```

## Implementation Plan

### Phase 1: Core Data Structure (Week 1)
   - **File**: `conversation_tree.py` - Core data models and basic operations
   - Implement `TreeNode`, `ConversationMetadata`, `OrganizationData` dataclasses
   - Create `MetadataStore` with JSON persistence and atomic file operations
   - Build basic `TreeManager` operations (create, move, delete, find)
   - Implement materialized path calculation (`/folder1/subfolder2/`)
   - Write comprehensive unit tests with 95%+ coverage
   - **Deliverable**: Standalone tree management with file persistence

### Phase 2: CLI Integration (Week 2)
   - **File**: Extend `chatgpt_browser.py` with tree functionality
   - Add `ConversationOrganizer` class integrating tree + existing loaders
   - Extend `ChatGPTBrowserCLI` with `organize` subcommand
   - Add organization file path resolution (`conversations_organization.json`)
   - Implement CLI commands: `create-folder`, `move`, `tag`, `list-tree`
   - Add migration tool for existing flat structure to tree
   - **Deliverable**: Full CLI tree management without TUI changes

### Phase 3: TUI Tree View (Week 3)
   - **File**: Extend `chatgpt_tui.py` with tree visualization
   - Add `TREE_VIEW` mode to `ViewMode` enum
   - Create `TreeListView` component with expand/collapse
   - Implement Unicode tree rendering (`├─`, `└─`, `│ `) 
   - Add keyboard shortcuts (Space: expand/collapse, Tab: switch views)
   - Integrate with existing navigation and search
   - **Deliverable**: Visual tree navigation in TUI

### Phase 4: Advanced Organization (Week 4)
   - **File**: `tree_operations.py` - Advanced tree manipulation
   - Implement drag-drop style commands (`move-to`, `copy-to`)
   - Add tag-based filtering and search within tree structure
   - Create import/export for organization templates
   - Add bulk operations (multi-select, batch move/tag)
   - Implement auto-organization suggestions based on content
   - **Deliverable**: Power-user organization features

## Testing Strategy

### Unit Tests (`test_conversation_tree.py`)
```python
class TestTreeManager:
    def test_create_folder()
    def test_move_node_to_folder()
    def test_delete_node_cascade()
    def test_path_calculation()
    def test_find_by_path()
    def test_cycle_detection()

class TestMetadataStore:
    def test_save_load_roundtrip()
    def test_atomic_write_with_backup()
    def test_corruption_recovery()
    def test_migration_from_v1_0()

class TestDataModels:
    def test_tree_node_serialization()
    def test_conversation_metadata_defaults()
    def test_organization_data_validation()
```

### Integration Tests (`test_tree_integration.py`)
- **CLI Integration**: Test `organize` commands with real conversation data
- **TUI Integration**: Mock curses testing for tree view navigation
- **File Operations**: Atomic write, backup/restore, concurrent access
- **Performance**: Load/save times with 10,000+ conversations and 1,000+ folders
- **Cross-platform**: Path handling on Windows/macOS/Linux
- **Migration**: Upgrade existing organization files between versions

### TUI Tests (`test_tree_tui.py`)
```python
class TestTreeView:
    def test_tree_rendering_unicode()
    def test_expand_collapse_navigation()
    def test_search_within_tree()
    def test_keyboard_shortcuts()
    def test_view_mode_switching()
```

### Performance Tests
- Load 10,000 conversations into tree structure < 500ms
- Tree rendering with 1,000 folders < 100ms
- Search within organized tree < 200ms
- File save operations < 50ms with atomic guarantees

## Observability

### Logging
- Tree operations: create/move/delete with node IDs
- File I/O operations: save/load with timing metrics
- Error conditions: corruption detection, recovery attempts
- Performance: operation timing for large datasets
- Structured JSON logging format for analysis

### Metrics
- Tree depth and breadth statistics
- Most frequently accessed folders/conversations
- Search query patterns and performance
- File size growth over time
- User interaction patterns in TUI

## Future Considerations

### Potential Enhancements
- **Smart Organization**: AI-powered auto-categorization based on conversation content using embeddings
- **Templates**: Shared organization templates (export/import common folder structures)
- **External Integration**: Sync with Obsidian, Notion, or other note-taking systems
- **Advanced UI**: Mouse support, drag-and-drop in TUI, web interface
- **Relationship Mapping**: Detect and visualize related/follow-up conversations
- **Collaboration**: Multi-user organization with conflict resolution
- **Advanced Search**: Full-text search within organized structure with ranking
- **Analytics**: Usage patterns, folder access frequency, optimization suggestions

### Known Limitations
- **Performance**: Large trees (>1000 folders) may impact TUI rendering (could optimize with virtualization)
- **Concurrency**: No real-time collaboration on organization structure
- **History**: Limited undo/redo for organization changes (could add command pattern)
- **Scale**: JSON format may become unwieldy for very large datasets (could migrate to SQLite)
- **Conflicts**: No merge strategy for conflicting organization changes
- **Memory**: Entire tree loaded in memory (could implement lazy loading for huge datasets)

### Migration Strategy
- **V1.0 → V1.1**: Add new fields with backward compatibility
- **JSON → SQLite**: Seamless migration for datasets >100MB
- **Folder Structure**: Preserve existing folder hierarchy during upgrades

## Dependencies

### Runtime Dependencies
```python
# Existing dependencies (no additions required)
Python >= 3.8  # dataclasses, pathlib, typing

# Standard library modules used:
json           # JSON serialization
uuid           # Folder ID generation  
datetime       # Timestamps
pathlib        # File path handling
shutil         # Atomic file operations
tempfile       # Safe temporary files
logging        # Error reporting
curses         # TUI integration (existing)
```

### Development Dependencies
```python
# Testing
pytest >= 6.0          # Test framework
pytest-cov >= 2.0       # Coverage reporting
pytest-mock >= 3.0      # Mocking for file operations

# Code Quality  
mypy >= 0.800          # Type checking
black >= 21.0          # Code formatting
flake8 >= 3.8          # Linting

# Development Tools
pre-commit >= 2.0      # Git hooks for quality
twine >= 3.0           # Package publishing (if needed)
```

### Version Compatibility
- **Python 3.8+**: Required for dataclass features, pathlib improvements
- **Backward Compatibility**: All existing CLI/TUI functionality unchanged
- **Forward Compatibility**: JSON format designed for easy schema evolution

## Security Considerations

### Data Privacy
- **Content Isolation**: Auxiliary file contains only UUIDs and user-generated metadata (no ChatGPT content)
- **File Permissions**: Restrictive permissions (0600) - readable/writable by user only
- **No Network**: Zero external network dependencies, all data stays local
- **Backup Security**: Backup files inherit same restrictive permissions

### Input Validation
```python
class InputValidator:
    @staticmethod
    def validate_folder_name(name: str) -> str:
        # Prevent path traversal, control characters, excessive length
        if not name or len(name) > 255:
            raise ValueError("Invalid folder name length")
        if any(char in name for char in ['/', '\\', '\0', '\n', '\r']):
            raise ValueError("Invalid characters in folder name")
        return name.strip()
    
    @staticmethod
    def validate_tags(tags: Set[str]) -> Set[str]:
        validated = set()
        for tag in tags:
            if len(tag) <= 50 and tag.isprintable():
                validated.add(tag.strip())
        return validated
```

### File System Security
- **Atomic Operations**: Prevent corruption during concurrent access
- **Path Validation**: All file operations use resolved absolute paths
- **Symlink Protection**: Refuse to follow symbolic links
- **Disk Space**: Check available space before large operations

## Rollout Strategy

### Phase 1: Core Development (Weeks 1-2)
- ✅ **Design Review**: Validate approach with existing codebase
- 🔄 **Core Implementation**: TreeManager, MetadataStore, data models
- ⏳ **CLI Integration**: Basic organize commands without TUI
- ⏳ **Testing**: Unit tests with 95%+ coverage, integration tests
- **Milestone**: CLI tree management fully functional

### Phase 2: TUI Integration (Weeks 3-4)
- **Tree View**: Add tree visualization to existing TUI
- **Navigation**: Keyboard shortcuts, expand/collapse, search
- **Polish**: Unicode rendering, performance optimization
- **Testing**: TUI integration tests, manual testing
- **Milestone**: Complete tree navigation in TUI

### Phase 3: Advanced Features (Weeks 5-6)
- **Organization**: Drag-drop commands, bulk operations
- **Search**: Advanced search within tree structure
- **Import/Export**: Template system, migration tools
- **Performance**: Optimize for large datasets
- **Milestone**: Power-user features complete

### Phase 4: Production Release (Week 7)
- **Documentation**: Update README, add examples
- **Migration**: Tool for existing users to organize conversations
- **Performance Testing**: Validate with 10,000+ conversations
- **Release**: Tag v2.0 with tree organization features

### Success Metrics
- 📊 **Performance**: Tree operations < 100ms, file save < 50ms
- 🧪 **Quality**: 95%+ test coverage, zero critical bugs
- 👥 **Usability**: Existing users can upgrade seamlessly
- 📈 **Adoption**: Tree view becomes default mode for power users

## References
- Firefox Tree Style Tabs: https://github.com/piroor/treestyletab
- Adjacency List vs Nested Sets: https://stackoverflow.com/questions/889788
- ChatGPT Export Format: OpenAI conversation export schema
- Related design patterns: Composite Pattern, Repository Pattern