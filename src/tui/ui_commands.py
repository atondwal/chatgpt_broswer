#!/usr/bin/env python3
"""
UI command constants for the ChatGPT TUI.

Provides named constants for all user interface commands to eliminate magic strings
and make the code self-documenting.
"""

from enum import Enum


class UICommand:
    """Named constants for all TUI commands."""
    
    # Application lifecycle commands
    QUIT_APPLICATION = "quit_application"
    REFRESH_VIEW = "refresh_view"
    
    # Navigation commands
    MOVE_UP = "move_up"
    MOVE_DOWN = "move_down"
    PAGE_UP = "page_up"
    PAGE_DOWN = "page_down"
    MOVE_TO_TOP = "move_to_top"
    MOVE_TO_BOTTOM = "move_to_bottom"
    
    # View switching commands
    SWITCH_TO_LIST_VIEW = "switch_to_list_view"
    SWITCH_TO_TREE_VIEW = "switch_to_tree_view"
    SWITCH_TO_SEARCH_VIEW = "switch_to_search_view"
    SWITCH_TO_DETAIL_VIEW = "switch_to_detail_view"
    
    # Search commands
    START_SEARCH_MODE = "start_search_mode"
    SUBMIT_SEARCH_QUERY = "submit_search_query"
    CANCEL_SEARCH_MODE = "cancel_search_mode"
    
    # Conversation commands
    SELECT_CONVERSATION = "select_conversation"
    EXPORT_CONVERSATION = "export_conversation"
    VIEW_CONVERSATION_DETAILS = "view_conversation_details"
    CLOSE_CONVERSATION_DETAILS = "close_conversation_details"
    
    # Tree management commands
    CREATE_NEW_FOLDER = "create_new_folder"
    RENAME_SELECTED_ITEM = "rename_selected_item"
    DELETE_SELECTED_ITEM = "delete_selected_item"
    MOVE_SELECTED_ITEM = "move_selected_item"
    TOGGLE_FOLDER_EXPANSION = "toggle_folder_expansion"
    
    # Help and information commands
    SHOW_HELP_SCREEN = "show_help_screen"
    SHOW_KEYBOARD_SHORTCUTS = "show_keyboard_shortcuts"


class ViewMode(Enum):
    """Enumeration of available view modes in the TUI."""
    CONVERSATION_LIST = "conversation_list"
    CONVERSATION_TREE = "conversation_tree"
    CONVERSATION_DETAIL = "conversation_detail"
    SEARCH_MODE = "search_mode"
    HELP_SCREEN = "help_screen"


class KeyboardShortcut:
    """Named constants for keyboard shortcuts."""
    
    # Navigation keys
    ARROW_UP = "↑"
    ARROW_DOWN = "↓"
    ARROW_LEFT = "←"
    ARROW_RIGHT = "→"
    
    # Special keys
    ENTER = "Enter"
    ESCAPE = "Esc"
    SPACE = "Space"
    BACKSPACE = "Backspace"
    DELETE = "Delete"
    
    # Letter keys for commands
    QUIT_KEY = "q"
    HELP_KEY = "?"
    SEARCH_KEY = "/"
    ALTERNATIVE_SEARCH_KEY = "s"
    TREE_VIEW_KEY = "t"
    LIST_VIEW_KEY = "l"
    
    # Tree management keys
    NEW_FOLDER_KEY = "n"
    RENAME_KEY = "r"
    DELETE_KEY = "d"
    MOVE_KEY = "m"
    
    # Page navigation
    PAGE_UP_KEY = "Page Up"
    PAGE_DOWN_KEY = "Page Down"
    HOME_KEY = "Home"
    END_KEY = "End"


class StatusMessage:
    """Predefined status messages for user feedback."""
    
    # View switching messages
    SWITCHED_TO_LIST_VIEW = "Switched to conversation list view"
    SWITCHED_TO_TREE_VIEW = "Switched to tree organization view"
    ENTERED_SEARCH_MODE = "Search mode activated - type to filter conversations"
    EXITED_SEARCH_MODE = "Search mode cancelled"
    
    # Search messages
    SEARCH_RESULTS_FOUND = "Found {count} conversations matching '{term}'"
    NO_SEARCH_RESULTS = "No conversations found matching '{term}'"
    SEARCH_APPLIED = "Filter applied: showing results for '{term}'"
    
    # Conversation messages
    CONVERSATION_SELECTED = "Viewing conversation: {title}"
    CONVERSATION_EXPORTED = "Conversation exported successfully"
    RETURNED_TO_CONVERSATION_LIST = "Returned to conversation list"
    
    # Tree management messages
    FOLDER_CREATED = "Created folder '{name}' successfully"
    ITEM_RENAMED = "Renamed to '{new_name}' successfully"
    ITEM_DELETED = "Deleted {item_type} '{name}' successfully"
    ITEM_MOVED = "Moved '{name}' to {destination} successfully"
    FOLDER_TOGGLED = "Folder expansion toggled"
    
    # Error messages
    NO_ITEM_SELECTED = "No item selected"
    OPERATION_CANCELLED = "Operation cancelled by user"
    INVALID_FOLDER_NAME = "Folder name cannot be empty"
    
    # Loading messages
    LOADING_CONVERSATIONS = "Loading conversations..."
    ORGANIZING_CONVERSATIONS = "Organizing conversation tree..."


class ErrorMessage:
    """Predefined error messages for consistent user feedback."""
    
    # File operation errors
    CONVERSATION_FILE_NOT_FOUND = "Conversation file not found: {path}"
    CONVERSATION_FILE_INVALID = "Invalid conversation file format: {path}"
    ORGANIZATION_FILE_CORRUPTED = "Organization file corrupted, using backup"
    
    # Tree operation errors
    FOLDER_NAME_EMPTY = "Folder name cannot be empty"
    FOLDER_NAME_TOO_LONG = "Folder name exceeds maximum length of {max_length} characters"
    MAXIMUM_TREE_DEPTH_EXCEEDED = "Maximum tree depth of {max_depth} exceeded"
    MAXIMUM_CHILDREN_EXCEEDED = "Maximum children per folder ({max_children}) exceeded"
    CYCLE_DETECTED_IN_MOVE = "Move operation would create a cycle in the tree"
    PARENT_FOLDER_NOT_FOUND = "Parent folder '{parent_id}' does not exist"
    
    # UI operation errors
    TERMINAL_TOO_SMALL = "Terminal window too small (minimum {min_width}x{min_height})"
    UNSUPPORTED_OPERATION = "Operation not supported in current view mode"
    KEYBOARD_INTERRUPT = "Operation interrupted by user"