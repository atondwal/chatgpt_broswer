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
from src.core.models import Conversation, MessageRole
from src.core.conversation_operations import ConversationLoader, ConversationSearcher, ConversationExporter
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
from src.tui.search_view import SearchView
from src.tui.detail_view import ConversationDetailView


class ViewMode(Enum):
    """Available view modes in the TUI."""
    CONVERSATION_LIST = "list"
    CONVERSATION_TREE = "tree"
    CONVERSATION_DETAIL = "detail"
    SEARCH = "search"
    HELP = "help"








class ConversationListView(NavigableListView):
    """Conversation list with search filtering."""
    
    def __init__(self, stdscr, y, x, width, height):
        super().__init__(stdscr, y, x, width, height)
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


class TreeView(NavigableListView):
    """Tree view with folder management."""
    
    def __init__(self, stdscr, y, x, width, height, organizer: ConversationOrganizer):
        super().__init__(stdscr, y, x, width, height)
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


class ChatGPTTUI:
    """Terminal interface for browsing ChatGPT conversations."""
    
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
        
        # UI components
        self.stdscr = None
        self.list_view = None
        self.tree_view = None
        self.search_view = None
        self.detail_view = None
        self.current_conversation = None
        
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
        for i, (fg, bg) in enumerate([
            (curses.COLOR_WHITE, -1),      # DEFAULT
            (curses.COLOR_CYAN, curses.COLOR_BLUE),   # HEADER
            (curses.COLOR_BLACK, curses.COLOR_WHITE), # SELECTED
            (curses.COLOR_BLUE, -1),       # BORDER
            (curses.COLOR_WHITE, curses.COLOR_BLUE),  # STATUS
        ], 1):
            curses.init_pair(i, fg, bg)
        
    def _init_ui_components(self) -> None:
        """Initialize UI components."""
        height, width = self.stdscr.getmaxyx()
        content_height = height - 1  # Leave space for status
        
        self.list_view = ConversationListView(self.stdscr, 0, 0, width, content_height)
        self.list_view.set_conversations(self.conversations)
        
        self.tree_view = TreeView(self.stdscr, 0, 0, width, content_height, self.organizer)
        self.tree_view.set_conversations(self.conversations)
        
        self.search_view = SearchView(self.stdscr, 0, 0, width, 1)
        self.search_view.set_search_callback(self._on_search_changed)
        
        self.detail_view = ConversationDetailView(self.stdscr, 1, 0, width, content_height - 1)
        
    def _handle_input(self, key: int) -> None:
        """Handle user input."""
        if self.current_view == ViewMode.SEARCH:
            result = self.search_view.handle_input(key)
            self._process_command(result)
        elif self.current_view == ViewMode.CONVERSATION_DETAIL:
            result = self.detail_view.handle_input(key)
            self._process_command(result)
        elif self.current_view == ViewMode.CONVERSATION_LIST:
            result = self.list_view.handle_input(key)
            self._process_command(result)
        elif self.current_view == ViewMode.CONVERSATION_TREE:
            result = self.tree_view.handle_input(key)
            self._process_command(result)
            
    def _process_command(self, command: Optional[str]) -> None:
        """Process command from view."""
        if not command:
            return
            
        commands = {
            "quit": lambda: setattr(self, 'running', False),
            "start_search": self._start_search,
            "search_cancelled": self._cancel_search,
            "search_submitted": self._submit_search,
            "select_conversation": self._select_conversation,
            "close_detail": self._close_detail,
            "toggle_tree_view": lambda: self._switch_view(ViewMode.CONVERSATION_TREE, "tree"),
            "toggle_list_view": lambda: self._switch_view(ViewMode.CONVERSATION_LIST, "list"),
            "show_help": self._show_help,
        }
        
        # Tree-only commands
        if self.current_view == ViewMode.CONVERSATION_TREE:
            commands.update({
                "toggle_folder": lambda: (self.tree_view.toggle_folder(), setattr(self, 'status_message', "Toggled folder")),
                "create_folder": self._create_folder,
                "rename_item": self._rename_item,
                "delete_item": self._delete_item,
                "move_item": self._move_item,
            })
        
        try:
            if command in commands:
                result = commands[command]()
                if isinstance(result, tuple):  # Handle multiple operations
                    pass  # Already executed
            else:
                self.status_message = f"Unknown command: {command}"
        except Exception as e:
            self.status_message = f"Error: {str(e)}"
            self.logger.error(f"Command {command} failed: {e}")
            
    def _create_folder(self) -> None:
        """Create new folder."""
        name = get_folder_name_input(self.stdscr, "Folder name:")
        if not name:
            return
            
        try:
            # Use selected folder as parent if it's a folder
            parent_id = None
            selected = self.tree_view.get_selected_node()
            if selected and selected.node_type == NodeType.FOLDER:
                parent_id = selected.id
            
            self.organizer.create_folder(name, parent_id)
            self.tree_view.refresh_tree()
            self.status_message = f"Created '{name}'"
        except Exception as e:
            self.status_message = f"Create failed: {e}"
            
    def _rename_item(self) -> None:
        """Rename selected item."""
        selected = self.tree_view.get_selected_node()
        if not selected:
            self.status_message = "Nothing selected"
            return
            
        new_name = get_folder_name_input(self.stdscr, f"Rename '{selected.name}':", selected.name)
        if not new_name or new_name == selected.name:
            return
            
        try:
            selected.name = new_name
            self.organizer.save_organization()
            self.tree_view.refresh_tree()
            self.status_message = f"Renamed to '{new_name}'"
        except Exception as e:
            self.status_message = f"Rename failed: {e}"
            
    def _delete_item(self) -> None:
        """Delete selected item."""
        selected = self.tree_view.get_selected_node()
        if not selected:
            self.status_message = "Nothing selected"
            return
            
        item_type = "folder" if selected.node_type == NodeType.FOLDER else "conversation"
        if not confirm_delete(self.stdscr, selected.name, item_type):
            return
            
        try:
            self.organizer.tree_manager.delete_node(selected.id)
            self.organizer.save_organization()
            self.tree_view.refresh_tree()
            self.status_message = f"Deleted {item_type}"
        except Exception as e:
            self.status_message = f"Delete failed: {e}"
            
    def _move_item(self) -> None:
        """Move selected item."""
        selected = self.tree_view.get_selected_node()
        if not selected:
            self.status_message = "Nothing selected"
            return
            
        folder_manager = FolderManager(self.stdscr)
        current_pos = self.tree_view.scroll_state.selected
        destination_id = folder_manager.select_folder(self.tree_view.tree_items, current_pos)
        
        if destination_id == selected.id:
            self.status_message = "Cannot move to itself"
            return
            
        try:
            self.organizer.tree_manager.move_node(selected.id, destination_id)
            self.organizer.save_organization()
            self.tree_view.refresh_tree()
            dest = "root" if destination_id is None else "folder"
            self.status_message = f"Moved to {dest}"
        except Exception as e:
            self.status_message = f"Move failed: {e}"
    
    def _switch_view(self, view: ViewMode, name: str) -> None:
        """Switch to specified view."""
        self.current_view = view
        self.status_message = f"Switched to {name} view"
    
    def _start_search(self) -> None:
        """Start search mode."""
        self.current_view = ViewMode.SEARCH
        self.search_view.activate()
        self.status_message = "Search mode"
    
    def _cancel_search(self) -> None:
        """Cancel search."""
        self.search_view.deactivate()
        self._switch_view(ViewMode.CONVERSATION_LIST, "list")
    
    def _submit_search(self) -> None:
        """Submit search."""
        term = self.search_view.get_search_term()
        self.search_view.deactivate()
        self.current_view = ViewMode.CONVERSATION_LIST
        self.status_message = f"Results for: '{term}'" if term else "All conversations"
    
    def _on_search_changed(self, search_term: str) -> None:
        """Handle search term changes."""
        if self.list_view:
            self.list_view.filter_conversations(search_term)
    
    def _select_conversation(self) -> None:
        """Select and view a conversation in detail."""
        if self.current_view == ViewMode.CONVERSATION_LIST:
            conversation = self.list_view.get_selected_conversation()
        elif self.current_view == ViewMode.CONVERSATION_TREE:
            conversation = self.tree_view.get_selected_conversation()
        else:
            return
            
        if conversation:
            self.current_conversation = conversation
            self.detail_view.set_conversation(conversation)
            self.current_view = ViewMode.CONVERSATION_DETAIL
            self.status_message = f"Viewing: {conversation.title}"
    
    def _close_detail(self) -> None:
        """Close detail view and return to previous view."""
        self.detail_view.clear_conversation()
        self.current_conversation = None
        self.current_view = ViewMode.CONVERSATION_LIST
        self.status_message = "Returned to conversation list"
            
    def _show_help(self) -> None:
        """Show shortcuts."""
        help_text = {
            ViewMode.CONVERSATION_LIST: "↑/↓:Navigate Enter:Select t:Tree /:Search q:Quit",
            ViewMode.CONVERSATION_TREE: "↑/↓:Navigate Enter:Open n:New r:Rename d:Delete m:Move l:List q:Quit",
            ViewMode.SEARCH: "Type:Filter Enter:Apply ESC:Cancel",
            ViewMode.CONVERSATION_DETAIL: "↑/↓:Scroll PgUp/PgDn:Page q/ESC:Back",
        }
        
        text = help_text.get(self.current_view, "q:Quit")
        height, width = self.stdscr.getmaxyx()
        status_y = height - 1
        
        try:
            truncated = text[:width-2]
            self.stdscr.addstr(status_y, 1, truncated, curses.color_pair(5))
        except curses.error:
            pass
        
    def _draw_screen(self) -> None:
        """Draw screen."""
        self.stdscr.clear()
        
        # Draw main content
        views = {
            ViewMode.CONVERSATION_LIST: self.list_view,
            ViewMode.CONVERSATION_TREE: self.tree_view,
            ViewMode.CONVERSATION_DETAIL: self.detail_view,
        }
        
        if self.current_view in views:
            views[self.current_view].draw()
        elif self.current_view == ViewMode.SEARCH:
            self.list_view.draw()  # Background
            self.search_view.draw()  # Overlay
            
        # Draw status
        self._draw_status()
        self.stdscr.refresh()
    
    def _draw_status(self) -> None:
        """Draw status line."""
        height, width = self.stdscr.getmaxyx()
        status_y = height - 1
        
        try:
            self.stdscr.move(status_y, 0)
            self.stdscr.clrtoeol()
            
            if self.status_message:
                msg = self.status_message[:width-2]  # Truncate if needed
                self.stdscr.addstr(status_y, 1, msg, curses.color_pair(5))  # STATUS color
                self.status_message = ""  # Clear after showing
            else:
                self._show_help()  # Show shortcuts by default
        except curses.error:
            pass


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="ChatGPT History Browser")
    parser.add_argument("conversations_file", help="Path to conversations.json file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if not Path(args.conversations_file).exists():
        print(f"File not found: {args.conversations_file}")
        sys.exit(1)
    
    try:
        tui = ChatGPTTUI(args.conversations_file, debug=args.debug)
        curses.wrapper(tui.run)
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()