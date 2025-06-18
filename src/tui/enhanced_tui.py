#!/usr/bin/env python3
"""
Enhanced ChatGPT History Browser TUI

Improved version using the new UI base classes and enhanced tree functionality.
"""

# Standard library imports
import argparse
import curses
import logging
import sys
import textwrap
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

# Local imports
from src.core.chatgpt_browser import (
    Conversation, ConversationLoader, ConversationSearcher, 
    ConversationExporter, MessageRole
)
from src.tree.conversation_tree import (
    ConversationOrganizer, TreeNode, NodeType, ConversationMetadata
)
from src.tree.tree_constants import TREE_CHARS, UI_CONSTANTS, COLOR_PAIRS, SHORTCUTS
from src.tui.ui_base import (
    BaseView, NavigableListView, ScrollState, InputHandler, UIFormatter
)
from src.tui.folder_management import (
    get_folder_name_input, confirm_delete, show_error_message, show_success_message,
    FolderManager
)


class ViewMode(Enum):
    """Available view modes in the TUI."""
    CONVERSATION_LIST = "list"
    CONVERSATION_TREE = "tree"
    CONVERSATION_DETAIL = "detail"
    SEARCH = "search"
    HELP = "help"


class ColorPair(Enum):
    """Color pairs for the TUI."""
    DEFAULT = COLOR_PAIRS["DEFAULT"]
    HEADER = COLOR_PAIRS["HEADER"]
    SELECTED = COLOR_PAIRS["SELECTED"]
    BORDER = COLOR_PAIRS["BORDER"]
    STATUS = COLOR_PAIRS["STATUS"]
    USER_MESSAGE = COLOR_PAIRS["USER_MESSAGE"]
    ASSISTANT_MESSAGE = COLOR_PAIRS["ASSISTANT_MESSAGE"]
    SYSTEM_MESSAGE = COLOR_PAIRS["SYSTEM_MESSAGE"]
    SEARCH_HIGHLIGHT = COLOR_PAIRS["SEARCH_HIGHLIGHT"]
    ERROR = COLOR_PAIRS["ERROR"]
    FOLDER = COLOR_PAIRS["FOLDER"]
    CONVERSATION_TREE = COLOR_PAIRS["CONVERSATION_TREE"]


@dataclass
class WindowDimensions:
    """Represents window dimensions and positions."""
    height: int
    width: int
    start_y: int = 0
    start_x: int = 0

    @property
    def max_y(self) -> int:
        return self.start_y + self.height - 1

    @property
    def max_x(self) -> int:
        return self.start_x + self.width - 1


class StatusBar:
    """Enhanced status bar with better messaging."""
    
    def __init__(self, stdscr, y: int, width: int):
        self.stdscr = stdscr
        self.y = y
        self.width = width
        self.message = ""
        self.error = False

    def show_message(self, message: str, is_error: bool = False) -> None:
        """Display a message in the status bar."""
        self.message = UIFormatter.truncate_text(message, self.width - 2)
        self.error = is_error
        self.refresh()

    def show_shortcuts(self, shortcuts: Dict[str, str]) -> None:
        """Display keyboard shortcuts in the status bar."""
        shortcut_items = []
        for key, desc in shortcuts.items():
            # Use consistent shortcut formatting
            if key in SHORTCUTS:
                key_display = SHORTCUTS[key][0] if SHORTCUTS[key] else key
            else:
                key_display = key
            shortcut_items.append(f"{key_display}: {desc}")
        
        shortcut_text = " | ".join(shortcut_items)
        self.message = UIFormatter.truncate_text(shortcut_text, self.width - 2)
        self.error = False
        self.refresh()

    def refresh(self) -> None:
        """Refresh the status bar display."""
        try:
            self.stdscr.move(self.y, 0)
            self.stdscr.clrtoeol()
            
            color = ColorPair.ERROR.value if self.error else ColorPair.STATUS.value
            if self.message:
                self.stdscr.addstr(self.y, 1, self.message, curses.color_pair(color))
        except curses.error:
            pass


class EnhancedConversationListView(NavigableListView):
    """Enhanced conversation list view with improved navigation and search."""
    
    def __init__(self, stdscr, dimensions: WindowDimensions):
        super().__init__(stdscr, dimensions.start_y, dimensions.height)
        self.dims = dimensions
        self.conversations: List[Conversation] = []
        self.filtered_conversations: List[Tuple[int, Conversation]] = []
        self.search_term = ""
        
    def set_conversations(self, conversations: List[Conversation]) -> None:
        """Set the conversations to display."""
        self.conversations = conversations
        self.filtered_conversations = [(i, conv) for i, conv in enumerate(conversations)]
        self.items = self.filtered_conversations
        self.scroll_state.reset()

    def filter_conversations(self, search_term: str) -> None:
        """Filter conversations based on search term."""
        self.search_term = search_term.lower()
        if not self.search_term:
            self.filtered_conversations = [(i, conv) for i, conv in enumerate(self.conversations)]
        else:
            self.filtered_conversations = [
                (i, conv) for i, conv in enumerate(self.conversations)
                if self.search_term in conv.title.lower()
            ]
        self.items = self.filtered_conversations
        self.scroll_state.reset()

    def get_selected_conversation(self) -> Optional[Conversation]:
        """Get the currently selected conversation."""
        selected_item = self.get_selected_item()
        if selected_item:
            _, conversation = selected_item
            return conversation
        return None

    def get_selected_index(self) -> int:
        """Get the original index of the selected conversation."""
        selected_item = self.get_selected_item()
        if selected_item:
            original_index, _ = selected_item
            return original_index
        return -1

    def format_item(self, item: Tuple[int, Conversation], index: int, is_selected: bool) -> str:
        """Format a conversation item for display."""
        original_index, conversation = item
        
        # Format timestamp
        try:
            timestamp_str = UIFormatter.format_timestamp(conversation.created_at)
        except (AttributeError, TypeError):
            timestamp_str = ""
        
        # Truncate title to fit
        max_title_length = self.width - 30  # Leave space for timestamp and margin
        title = UIFormatter.truncate_text(conversation.title, max_title_length)
        
        return f"{title:<{max_title_length}} {timestamp_str}"

    def draw(self) -> None:
        """Draw the conversation list."""
        title = f"Conversations ({len(self.filtered_conversations)})"
        if self.search_term:
            title += f" - Filter: '{self.search_term}'"
        self.draw_items(title)

    def handle_input(self, key: int) -> Optional[str]:
        """Handle input for conversation list."""
        # Try navigation first
        nav_result = self.handle_navigation_input(key)
        if nav_result:
            return nav_result
            
        # Handle other keys
        if InputHandler.is_enter_key(key):
            return "select_conversation"
        elif InputHandler.is_search_key(key):
            return "start_search"
        elif key == ord('t'):
            return "toggle_tree_view"
        elif key == ord('e'):
            return "export_conversation"
        elif InputHandler.is_help_key(key):
            return "show_help"
        elif InputHandler.is_quit_key(key):
            return "quit"
            
        return None


class EnhancedTreeListView(NavigableListView):
    """Enhanced tree view with folder management capabilities."""
    
    def __init__(self, stdscr, dimensions: WindowDimensions, organizer: ConversationOrganizer):
        super().__init__(stdscr, dimensions.start_y, dimensions.height)
        self.dims = dimensions
        self.organizer = organizer
        self.tree_items: List[Tuple[TreeNode, Optional[Conversation], int]] = []  # (node, conversation, depth)
        self.conversations_map: Dict[str, Conversation] = {}
        
    def set_conversations(self, conversations: List[Conversation]) -> None:
        """Set conversations and update tree display."""
        self.conversations_map = {conv.id: conv for conv in conversations}
        self.refresh_tree()

    def refresh_tree(self) -> None:
        """Refresh the tree display."""
        organized = self.organizer.get_organized_conversations(list(self.conversations_map.values()))
        self.tree_items = []
        
        def add_items_recursive(items: List[Tuple[TreeNode, Optional[Conversation]]], depth: int = 0):
            for tree_node, conversation in items:
                self.tree_items.append((tree_node, conversation, depth))
                
                # Add children if folder is expanded
                if (tree_node.node_type == NodeType.FOLDER and 
                    tree_node.expanded and 
                    hasattr(tree_node, 'children') and tree_node.children):
                    # Get children and recurse
                    children = []
                    for child_id in tree_node.children:
                        child_node = self.organizer.tree_manager.organization_data.tree_nodes.get(child_id)
                        if child_node:
                            child_conv = None
                            if child_node.node_type == NodeType.CONVERSATION:
                                child_conv = self.conversations_map.get(child_id)
                            children.append((child_node, child_conv))
                    
                    # Sort children: folders first, then by name
                    children.sort(key=lambda x: (x[0].node_type.value, x[0].name.lower()))
                    add_items_recursive(children, depth + 1)
        
        add_items_recursive(organized)
        self.items = self.tree_items
        
        # Preserve selection if possible
        if self.scroll_state.selected >= len(self.items):
            self.scroll_state.selected = max(0, len(self.items) - 1)

    def format_item(self, item: Tuple[TreeNode, Optional[Conversation], int], index: int, is_selected: bool) -> str:
        """Format a tree item for display."""
        tree_node, conversation, depth = item
        
        # Create indentation
        indent = TREE_CHARS["TREE_INDENT"] * depth
        
        # Choose icon and name
        if tree_node.node_type == NodeType.FOLDER:
            if tree_node.expanded:
                icon = TREE_CHARS["FOLDER_EXPANDED"]
            else:
                icon = TREE_CHARS["FOLDER_COLLAPSED"]
            icon += " " + TREE_CHARS["FOLDER_ICON"]
            name = tree_node.name
        else:
            icon = TREE_CHARS["CONVERSATION_ICON"]
            name = conversation.title if conversation else tree_node.name
        
        # Format the line
        max_name_length = self.width - len(indent) - len(icon) - 10
        display_name = UIFormatter.truncate_text(name, max_name_length)
        
        return f"{indent}{icon} {display_name}"

    def draw(self) -> None:
        """Draw the tree view."""
        folder_count = sum(1 for item in self.tree_items if item[0].node_type == NodeType.FOLDER)
        conv_count = sum(1 for item in self.tree_items if item[0].node_type == NodeType.CONVERSATION)
        title = f"Tree View - {folder_count} folders, {conv_count} conversations"
        
        self.draw_items(title)

    def handle_input(self, key: int) -> Optional[str]:
        """Handle input for tree view."""
        # Try navigation first
        nav_result = self.handle_navigation_input(key)
        if nav_result:
            return nav_result
        
        selected_item = self.get_selected_item()
        if not selected_item:
            return None
            
        tree_node, conversation, depth = selected_item
        
        # Handle tree-specific operations
        if InputHandler.is_enter_key(key):
            if tree_node.node_type == NodeType.FOLDER:
                return "toggle_folder"
            else:
                return "select_conversation"
        elif key == ord(' '):  # Space to toggle folder
            if tree_node.node_type == NodeType.FOLDER:
                return "toggle_folder"
        elif key == ord('n'):  # New folder
            return "create_folder"
        elif key == ord('r'):  # Rename
            return "rename_item"
        elif key == ord('d'):  # Delete
            return "delete_item"
        elif key == ord('m'):  # Move
            return "move_item"
        elif key == ord('l'):  # Switch to list view
            return "toggle_list_view"
        elif InputHandler.is_help_key(key):
            return "show_help"
        elif InputHandler.is_quit_key(key):
            return "quit"
            
        return None
    
    def get_selected_node(self) -> Optional[TreeNode]:
        """Get the selected tree node."""
        selected_item = self.get_selected_item()
        if selected_item:
            return selected_item[0]
        return None
    
    def get_selected_conversation(self) -> Optional[Conversation]:
        """Get the selected conversation if any."""
        selected_item = self.get_selected_item()
        if selected_item and selected_item[1]:
            return selected_item[1]
        return None
    
    def toggle_folder(self) -> None:
        """Toggle folder expansion."""
        selected_item = self.get_selected_item()
        if selected_item and selected_item[0].node_type == NodeType.FOLDER:
            tree_node = selected_item[0]
            tree_node.expanded = not tree_node.expanded
            self.refresh_tree()


class EnhancedChatGPTTUI:
    """Enhanced TUI with improved navigation and tree management."""
    
    def __init__(self, conversations_file: str, debug: bool = False):
        self.conversations_file = conversations_file
        self.debug = debug
        self.logger = self._setup_logging()
        
        # Load data
        self.loader = ConversationLoader()
        self.conversations = self.loader.load_conversations(conversations_file)
        self.organizer = ConversationOrganizer(conversations_file, debug=debug)
        
        # UI state
        self.current_view = ViewMode.CONVERSATION_LIST
        self.running = True
        self.status_message = ""
        
        # UI components (will be initialized in run)
        self.stdscr = None
        self.status_bar = None
        self.list_view = None
        self.tree_view = None
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger(__name__)
        if self.debug:
            logger.setLevel(logging.DEBUG)
        return logger
        
    def run(self, stdscr) -> None:
        """Main TUI loop."""
        self.stdscr = stdscr
        self._init_colors()
        self._init_ui_components()
        
        # Initial draw
        self._draw_screen()
        
        # Main event loop
        while self.running:
            try:
                key = stdscr.getch()
                self._handle_input(key)
                self._draw_screen()
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                if self.debug:
                    raise
                
    def _init_colors(self) -> None:
        """Initialize color pairs."""
        curses.start_color()
        curses.use_default_colors()
        
        # Define color pairs
        curses.init_pair(ColorPair.DEFAULT.value, curses.COLOR_WHITE, -1)
        curses.init_pair(ColorPair.HEADER.value, curses.COLOR_CYAN, curses.COLOR_BLUE)
        curses.init_pair(ColorPair.SELECTED.value, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(ColorPair.BORDER.value, curses.COLOR_BLUE, -1)
        curses.init_pair(ColorPair.STATUS.value, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(ColorPair.ERROR.value, curses.COLOR_WHITE, curses.COLOR_RED)
        curses.init_pair(ColorPair.FOLDER.value, curses.COLOR_YELLOW, -1)
        curses.init_pair(ColorPair.CONVERSATION_TREE.value, curses.COLOR_GREEN, -1)
        
    def _init_ui_components(self) -> None:
        """Initialize UI components."""
        height, width = self.stdscr.getmaxyx()
        
        # Status bar at bottom
        status_y = height - 1
        self.status_bar = StatusBar(self.stdscr, status_y, width)
        
        # Main content area
        content_height = height - UI_CONSTANTS["STATUS_BAR_HEIGHT"]
        content_dims = WindowDimensions(content_height, width, 0, 0)
        
        # Initialize views
        self.list_view = EnhancedConversationListView(self.stdscr, content_dims)
        self.list_view.set_conversations(self.conversations)
        
        self.tree_view = EnhancedTreeListView(self.stdscr, content_dims, self.organizer)
        self.tree_view.set_conversations(self.conversations)
        
    def _handle_input(self, key: int) -> None:
        """Handle user input."""
        if self.current_view == ViewMode.CONVERSATION_LIST:
            result = self.list_view.handle_input(key)
            self._process_command(result)
        elif self.current_view == ViewMode.CONVERSATION_TREE:
            result = self.tree_view.handle_input(key)
            self._process_command(result)
            
    def _process_command(self, command: Optional[str]) -> None:
        """Process a command from view input handling."""
        if not command:
            return
            
        try:
            if command == "quit":
                self.running = False
            elif command == "toggle_tree_view":
                self.current_view = ViewMode.CONVERSATION_TREE
                self.status_message = "Switched to tree view"
            elif command == "toggle_list_view":
                self.current_view = ViewMode.CONVERSATION_LIST  
                self.status_message = "Switched to list view"
            elif command == "toggle_folder" and self.current_view == ViewMode.CONVERSATION_TREE:
                self.tree_view.toggle_folder()
                self.status_message = "Toggled folder"
            elif command == "create_folder" and self.current_view == ViewMode.CONVERSATION_TREE:
                self._create_folder()
            elif command == "rename_item" and self.current_view == ViewMode.CONVERSATION_TREE:
                self._rename_item()
            elif command == "delete_item" and self.current_view == ViewMode.CONVERSATION_TREE:
                self._delete_item()
            elif command == "move_item" and self.current_view == ViewMode.CONVERSATION_TREE:
                self._move_item()
            elif command == "show_help":
                self._show_help()
            else:
                self.status_message = f"Command not implemented: {command}"
                
        except Exception as e:
            self.status_message = f"Error: {str(e)}"
            self.logger.error(f"Error processing command {command}: {e}")
            
    def _create_folder(self) -> None:
        """Create a new folder with user input."""
        try:
            # Get folder name from user
            folder_name = get_folder_name_input(self.stdscr, "Enter folder name:")
            
            if not folder_name:
                self.status_message = "Folder creation cancelled"
                return
            
            # Get parent folder if a folder is selected
            parent_id = None
            if self.current_view == ViewMode.CONVERSATION_TREE:
                selected_node = self.tree_view.get_selected_node()
                if selected_node and selected_node.node_type == NodeType.FOLDER:
                    parent_id = selected_node.id
            
            # Create the folder
            folder_id = self.organizer.create_folder(folder_name, parent_id)
            
            # Refresh tree view
            if hasattr(self, 'tree_view'):
                self.tree_view.refresh_tree()
            
            show_success_message(self.stdscr, f"Created folder '{folder_name}'")
            
        except Exception as e:
            show_error_message(self.stdscr, f"Failed to create folder: {str(e)}")
            
    def _rename_item(self) -> None:
        """Rename the selected item."""
        if self.current_view != ViewMode.CONVERSATION_TREE:
            self.status_message = "Rename only available in tree view"
            return
            
        try:
            selected_node = self.tree_view.get_selected_node()
            if not selected_node:
                self.status_message = "No item selected"
                return
            
            # Get new name from user
            current_name = selected_node.name
            new_name = get_folder_name_input(
                self.stdscr, 
                f"Rename '{current_name}':",
                current_name
            )
            
            if not new_name or new_name == current_name:
                self.status_message = "Rename cancelled"
                return
            
            # Update the node name
            selected_node.name = new_name
            
            # Save changes
            self.organizer.save_organization()
            
            # Refresh tree view
            self.tree_view.refresh_tree()
            
            show_success_message(self.stdscr, f"Renamed to '{new_name}'")
            
        except Exception as e:
            show_error_message(self.stdscr, f"Failed to rename: {str(e)}")
            
    def _delete_item(self) -> None:
        """Delete the selected item."""
        if self.current_view != ViewMode.CONVERSATION_TREE:
            self.status_message = "Delete only available in tree view"
            return
            
        try:
            selected_node = self.tree_view.get_selected_node()
            if not selected_node:
                self.status_message = "No item selected"
                return
            
            # Confirm deletion
            item_type = "folder" if selected_node.node_type == NodeType.FOLDER else "conversation"
            if not confirm_delete(self.stdscr, selected_node.name, item_type):
                self.status_message = "Delete cancelled"
                return
            
            # Delete the node
            self.organizer.tree_manager.delete_node(selected_node.id)
            
            # Save changes
            self.organizer.save_organization()
            
            # Refresh tree view
            self.tree_view.refresh_tree()
            
            show_success_message(self.stdscr, f"Deleted {item_type} '{selected_node.name}'")
            
        except Exception as e:
            show_error_message(self.stdscr, f"Failed to delete: {str(e)}")
            
    def _move_item(self) -> None:
        """Move the selected item to a different folder."""
        if self.current_view != ViewMode.CONVERSATION_TREE:
            self.status_message = "Move only available in tree view"
            return
            
        try:
            selected_node = self.tree_view.get_selected_node()
            if not selected_node:
                self.status_message = "No item selected"
                return
            
            # Get destination folder
            folder_manager = FolderManager(self.stdscr)
            selected_item = self.tree_view.get_selected_item()
            current_selection = self.tree_view.scroll_state.selected if selected_item else 0
            
            destination_id = folder_manager.select_folder(
                self.tree_view.tree_items, 
                current_selection
            )
            
            if destination_id == selected_node.id:
                self.status_message = "Cannot move item to itself"
                return
            
            # Move the node
            self.organizer.tree_manager.move_node(selected_node.id, destination_id)
            
            # Save changes
            self.organizer.save_organization()
            
            # Refresh tree view
            self.tree_view.refresh_tree()
            
            dest_name = "root" if destination_id is None else "selected folder"
            show_success_message(self.stdscr, f"Moved '{selected_node.name}' to {dest_name}")
            
        except Exception as e:
            show_error_message(self.stdscr, f"Failed to move: {str(e)}")
            
    def _show_help(self) -> None:
        """Show help shortcuts."""
        if self.current_view == ViewMode.CONVERSATION_LIST:
            shortcuts = {
                "↑/↓": "Navigate",
                "Enter": "Select",
                "t": "Tree view", 
                "/": "Search",
                "q": "Quit"
            }
        else:  # Tree view
            shortcuts = {
                "↑/↓": "Navigate",
                "Enter": "Open/Toggle",
                "Space": "Toggle folder",
                "n": "New folder",
                "r": "Rename",
                "d": "Delete",
                "m": "Move",
                "l": "List view",
                "q": "Quit"
            }
        self.status_bar.show_shortcuts(shortcuts)
        
    def _draw_screen(self) -> None:
        """Draw the entire screen."""
        self.stdscr.clear()
        
        if self.current_view == ViewMode.CONVERSATION_LIST:
            self.list_view.draw()
        elif self.current_view == ViewMode.CONVERSATION_TREE:
            self.tree_view.draw()
            
        # Update status bar
        if self.status_message:
            self.status_bar.show_message(self.status_message)
            self.status_message = ""  # Clear after showing
        else:
            self._show_help()  # Show help by default
            
        self.stdscr.refresh()


def main():
    """Main entry point for enhanced TUI."""
    parser = argparse.ArgumentParser(description="Enhanced ChatGPT History Browser")
    parser.add_argument("conversations_file", help="Path to conversations.json file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if not Path(args.conversations_file).exists():
        print(f"Error: Conversations file not found: {args.conversations_file}")
        sys.exit(1)
    
    try:
        tui = EnhancedChatGPTTUI(args.conversations_file, debug=args.debug)
        curses.wrapper(tui.run)
    except Exception as e:
        print(f"Error running TUI: {e}")
        if args.debug:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()