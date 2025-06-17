#!/usr/bin/env python3
"""
Type definitions and data structures for the conversation tree organization system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Union, Protocol, Any
from pathlib import Path

# Core enums
class NodeType(Enum):
    """Type of tree node."""
    FOLDER = "folder"
    CONVERSATION = "conversation"


class TreeOperation(Enum):
    """Types of tree operations for validation and logging."""
    CREATE_FOLDER = "create_folder"
    CREATE_CONVERSATION = "create_conversation"
    MOVE_NODE = "move_node"
    DELETE_NODE = "delete_node"
    UPDATE_METADATA = "update_metadata"


# Core data structures
@dataclass
class TreeNode:
    """Represents a node in the conversation tree."""
    id: str                    # UUID for folders, conversation_id for conversations
    name: str                  # Display name
    node_type: NodeType        # FOLDER or CONVERSATION
    parent_id: Optional[str] = None   # Parent node ID
    children: Set[str] = field(default_factory=set)  # Child node IDs
    path: str = ""             # Materialized path: "/Work/Python/"
    expanded: bool = True      # UI state

    def __post_init__(self):
        """Validate node data after initialization."""
        if not self.id:
            raise ValueError("Node ID cannot be empty")
        if not self.name:
            raise ValueError("Node name cannot be empty")
        if not isinstance(self.node_type, NodeType):
            if isinstance(self.node_type, str):
                self.node_type = NodeType(self.node_type)
            else:
                raise ValueError(f"Invalid node type: {self.node_type}")


@dataclass
class ConversationMetadata:
    """Metadata for a conversation."""
    conversation_id: str       # Links to Conversation.id
    custom_title: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    notes: str = ""
    favorite: bool = False

    def __post_init__(self):
        """Validate metadata after initialization."""
        if not self.conversation_id:
            raise ValueError("Conversation ID cannot be empty")


@dataclass
class OrganizationData:
    """Complete organization data structure."""
    tree_nodes: Dict[str, TreeNode] = field(default_factory=dict)
    conversation_metadata: Dict[str, ConversationMetadata] = field(default_factory=dict)
    root_nodes: Set[str] = field(default_factory=set)  # Top-level folder IDs
    version: str = "1.0"       # Schema version for migration

    def get_node_count(self) -> int:
        """Get total number of nodes."""
        return len(self.tree_nodes)
    
    def get_folder_count(self) -> int:
        """Get number of folder nodes."""
        return sum(1 for node in self.tree_nodes.values() 
                  if node.node_type == NodeType.FOLDER)
    
    def get_conversation_count(self) -> int:
        """Get number of conversation nodes."""
        return sum(1 for node in self.tree_nodes.values() 
                  if node.node_type == NodeType.CONVERSATION)


# Type aliases for better readability
NodeId = str
ConversationId = str
FolderId = str
FilePath = Union[str, Path]

# Tree traversal results
TreeOrderResult = List[TreeNode]
OrganizedConversations = List[tuple[TreeNode, Optional[Any]]]  # Any = Conversation

# Protocols for dependency injection
class ConversationProtocol(Protocol):
    """Protocol for conversation objects."""
    id: str
    title: str
    message_count: int


class FileStorageProtocol(Protocol):
    """Protocol for file storage operations."""
    def load(self) -> OrganizationData:
        """Load organization data."""
        ...
    
    def save(self, data: OrganizationData) -> None:
        """Save organization data."""
        ...


class TreeManagerProtocol(Protocol):
    """Protocol for tree management operations."""
    def create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """Create a new folder."""
        ...
    
    def move_node(self, node_id: str, new_parent_id: Optional[str]) -> None:
        """Move a node to a new parent."""
        ...
    
    def delete_node(self, node_id: str) -> None:
        """Delete a node and its descendants."""
        ...


# Configuration types
@dataclass
class TreeConfig:
    """Configuration for tree operations."""
    max_depth: int = 20
    max_children_per_folder: int = 1000
    enable_validation: bool = True
    enable_logging: bool = True
    cache_size: int = 128


@dataclass
class UIConfig:
    """Configuration for UI rendering."""
    show_message_counts: bool = True
    show_folder_icons: bool = True
    show_conversation_icons: bool = True
    tree_indent: str = "  "
    expand_char: str = "▼"
    collapse_char: str = "▶"


# Validation result types
@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)