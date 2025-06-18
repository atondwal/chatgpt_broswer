#!/usr/bin/env python3
"""
Constants and configuration for the conversation tree organization system.
"""

# Schema and versioning
DEFAULT_SCHEMA_VERSION = "1.0"

# File extensions and suffixes
ORGANIZATION_FILE_SUFFIX = "_organization.json"
BACKUP_FILE_SUFFIX = ".bak"
TEMP_FILE_SUFFIX = ".tmp"

# Validation limits
MAX_FOLDER_NAME_LENGTH = 255
MIN_FOLDER_NAME_LENGTH = 1
MAX_TREE_DEPTH = 20  # Prevent extremely deep nesting
MAX_CHILDREN_PER_FOLDER = 1000  # Reasonable limit for UI performance

# File permissions
ORGANIZATION_FILE_PERMISSIONS = 0o600  # User read/write only

# Performance tuning
DEFAULT_CACHE_SIZE = 128
MAX_TREE_NODES_FOR_FAST_OPERATIONS = 10000

# Unicode characters for tree visualization
TREE_CHARS = {
    "FOLDER_EXPANDED": "▼",
    "FOLDER_COLLAPSED": "▶",
    "SELECTION_INDICATOR": "▶",
    "FOLDER_ICON": "📁",
    "CONVERSATION_ICON": "💬",
    "TREE_INDENT": "  ",
    "SCROLL_BAR_FILLED": "█",
    "SCROLL_BAR_EMPTY": "░",
}

# Default metadata values
DEFAULT_CONVERSATION_METADATA = {
    "custom_title": None,
    "tags": set(),
    "notes": "",
    "favorite": False,
}

# Error message templates
ERROR_MESSAGES = {
    "EMPTY_FOLDER_NAME": "Folder name cannot be empty",
    "PARENT_NOT_FOUND": "Parent folder {parent_id} does not exist",
    "PARENT_NOT_FOLDER": "Parent must be a folder, not a conversation",
    "NODE_NOT_FOUND": "Node {node_id} does not exist",
    "CONVERSATION_EXISTS": "Conversation {conversation_id} already exists in tree",
    "CYCLE_DETECTED": "Move would create a cycle",
    "MAX_DEPTH_EXCEEDED": "Maximum tree depth ({max_depth}) exceeded",
    "MAX_CHILDREN_EXCEEDED": "Maximum children per folder ({max_children}) exceeded",
    "INVALID_NODE_TYPE": "Invalid node type: {node_type}",
}

# UI Constants
UI_CONSTANTS = {
    "HEADER_HEIGHT": 1,
    "STATUS_BAR_HEIGHT": 1,
    "BORDER_HEIGHT": 2,
    "MIN_TERMINAL_WIDTH": 80,
    "MIN_TERMINAL_HEIGHT": 24,
    "DEFAULT_PAGE_SIZE": 10,
    "SCROLL_MARGIN": 3,
    "MAX_TITLE_LENGTH": 60,
    "INDENT_SIZE": 2,
}

# Color pair definitions
COLOR_PAIRS = {
    "DEFAULT": 1,
    "HEADER": 2,
    "SELECTED": 3,
    "BORDER": 4,
    "STATUS": 5,
    "USER_MESSAGE": 6,
    "ASSISTANT_MESSAGE": 7,
    "SYSTEM_MESSAGE": 8,
    "SEARCH_HIGHLIGHT": 9,
    "ERROR": 10,
    "FOLDER": 11,
    "CONVERSATION_TREE": 12,
}

# Keyboard shortcuts
SHORTCUTS = {
    "QUIT": ["q", "ESC"],
    "HELP": ["?", "F1"],
    "SEARCH": ["/", "s"],
    "BACK": ["BACKSPACE", "b"],
    "ENTER": ["ENTER", "RETURN"],
    "UP": ["UP", "k"],
    "DOWN": ["DOWN", "j"],
    "PAGE_UP": ["PAGE_UP"],
    "PAGE_DOWN": ["PAGE_DOWN"],
    "HOME": ["HOME"],
    "END": ["END"],
    "REFRESH": ["r", "F5"],
    "EXPORT": ["e"],
    "TREE_VIEW": ["t"],
    "LIST_VIEW": ["l"],
}

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL_DEFAULT = "INFO"
LOG_LEVEL_DEBUG = "DEBUG"