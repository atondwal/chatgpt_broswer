#!/usr/bin/env python3
"""Type definitions for ChatGPT Browser."""

from typing import TypedDict, List, Dict, Any, Optional, Union, Protocol
from typing_extensions import NotRequired
from enum import Enum


# Configuration Types
class LogLevel(Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ExportFormat(Enum):
    """Export formats."""
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"


class ConversationFormat(Enum):
    """Conversation file formats."""
    AUTO = "auto"
    CHATGPT = "chatgpt"
    CLAUDE = "claude"


# Data Structure Types
class MessageDict(TypedDict):
    """ChatGPT message dictionary structure."""
    id: str
    role: str
    content: Union[str, Dict[str, Any]]
    create_time: NotRequired[Optional[float]]
    author: NotRequired[Optional[Dict[str, Any]]]
    metadata: NotRequired[Optional[Dict[str, Any]]]


class ConversationDict(TypedDict):
    """ChatGPT conversation dictionary structure."""
    id: str
    title: str
    create_time: Optional[float]
    update_time: Optional[float]
    messages: List[MessageDict]
    mapping: NotRequired[Optional[Dict[str, Any]]]
    moderation_results: NotRequired[Optional[List[Any]]]
    current_node: NotRequired[Optional[str]]


class ClaudeMessageDict(TypedDict):
    """Claude message dictionary structure."""
    type: str
    content: Union[str, List[Dict[str, Any]]]
    uuid: NotRequired[str]
    timestamp: NotRequired[str]


class ProjectMetadata(TypedDict):
    """Claude project metadata structure."""
    name: str
    path: str
    conversation_count: int
    last_modified: Optional[float]


# Configuration Types
class LoggingConfig(TypedDict):
    """Logging configuration structure."""
    level: str
    log_file: NotRequired[Optional[str]]
    format_string: NotRequired[Optional[str]]
    debug_mode: NotRequired[bool]


class ValidationConfig(TypedDict):
    """Validation configuration structure."""
    max_search_length: NotRequired[int]
    max_count: NotRequired[int]
    min_count: NotRequired[int]
    allowed_export_formats: NotRequired[List[str]]


# UI Types
class UIColors(TypedDict):
    """UI color configuration."""
    selected: int
    status: int
    folder: int


class KeyBinding(TypedDict):
    """Key binding configuration."""
    key: Union[int, str]
    action: str
    description: str
    context: NotRequired[str]


# Protocol Types
class Renderable(Protocol):
    """Protocol for renderable UI components."""
    
    def render(self) -> None:
        """Render the component."""
        ...
    
    def refresh(self) -> None:
        """Refresh the component."""
        ...


class Actionable(Protocol):
    """Protocol for components that handle actions."""
    
    def can_handle(self, action: str) -> bool:
        """Check if this component can handle the action."""
        ...
    
    def handle(self, action: str, context: Any) -> Any:
        """Handle the action."""
        ...


class Searchable(Protocol):
    """Protocol for searchable components."""
    
    def search(self, term: str) -> List[Any]:
        """Search for items matching the term."""
        ...
    
    def filter(self, predicate: Any) -> List[Any]:
        """Filter items using a predicate."""
        ...


# Type Aliases
TreeItemTuple = tuple[Optional[Any], Optional[Any], int]  # (node, conversation, depth)
SearchResult = tuple[str, List[Any]]  # (query, results)
ActionResult = tuple[bool, Optional[str], Optional[Any]]  # (success, message, data)
ValidationResult = Union[str, int, None]  # Validated value or None if invalid

# File path types
FilePath = Union[str, Any]  # PathLike
DirectoryPath = Union[str, Any]  # PathLike

# Screen coordinate types
ScreenCoordinate = tuple[int, int]  # (row, col)
ScreenDimensions = tuple[int, int]  # (height, width)

# Key input types
KeyInput = Union[int, str]
KeySequence = List[KeyInput]

# Time types
Timestamp = float
TimeRange = tuple[Optional[Timestamp], Optional[Timestamp]]

# Error types
ErrorCode = str
ErrorMessage = str
ErrorContext = Dict[str, Any]