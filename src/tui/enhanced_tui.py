#!/usr/bin/env python3
"""Terminal UI for browsing ChatGPT conversations."""

import argparse
import curses
import logging
import sys
import textwrap
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from src.core.models import Conversation, MessageRole
from src.core.conversation_operations import ConversationLoader, ConversationSearcher, ConversationExporter
from src.tree.conversation_tree import ConversationOrganizer, TreeNode, NodeType, ConversationMetadata
from src.tree.tree_constants import TREE_CHARS
from src.tui.folder_management import get_folder_name_input, confirm_delete, FolderManager
from src.tui.search_view import SearchView
from src.tui.detail_view import ConversationDetailView


class ViewMode(Enum):
    """Available view modes."""
    LIST = "list"
    TREE = "tree"
    DETAIL = "detail"
    SEARCH = "search"


class ChatGPTTUI:
    """Terminal interface for browsing ChatGPT conversations."""
    
    def __init__(self, conversations_file: str, debug: bool = False):
        self.conversations_file = conversations_file
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        if debug:
            self.logger.setLevel(logging.DEBUG)
        
        # Load data
        self.loader = ConversationLoader()
        self.conversations = self.loader.load_conversations(conversations_file)
        self.organizer = ConversationOrganizer(conversations_file, debug=debug)
        
        # UI state
        self.current_view = ViewMode.LIST
        self.running = True
        self.status_message = ""
        
        # List view state
        self.filtered_conversations = [(i, c) for i, c in enumerate(self.conversations)]
        self.list_offset = 0
        self.list_selected = 0
        
        # Tree view state
        self.tree_items = []  # List of (TreeNode, Optional[Conversation], depth)
        self.tree_offset = 0
        self.tree_selected = 0
        
        # Search state
        self.search_term = ""
        
    def run(self, stdscr) -> None:
        """Main UI loop."""
        self.stdscr = stdscr
        curses.start_color()
        curses.use_default_colors()
        
        # Simple color setup
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Selected
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)   # Status
        curses.init_pair(3, curses.COLOR_YELLOW, -1)                 # Folder
        
        # Initialize components
        height, width = stdscr.getmaxyx()
        self.search_view = SearchView(stdscr, 0, 0, width, 1)
        self.search_view.set_search_callback(self._on_search_changed)
        self.detail_view = ConversationDetailView(stdscr, 1, 0, width, height - 2)
        
        # Initialize tree
        self._refresh_tree()
        
        while self.running:
            try:
                self._draw()
                key = stdscr.getch()
                self._handle_key(key)
            except KeyboardInterrupt:
                break
            except Exception as e:
                if self.debug:
                    raise
                self.status_message = f"Error: {e}"
                
    def _draw(self) -> None:
        """Draw current view."""
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        if self.current_view == ViewMode.LIST:
            self._draw_list()
        elif self.current_view == ViewMode.TREE:
            self._draw_tree()
        elif self.current_view == ViewMode.DETAIL:
            self.detail_view.draw()
        elif self.current_view == ViewMode.SEARCH:
            self._draw_list()  # Background
            self.search_view.draw()  # Overlay
            
        # Status line
        if self.status_message:
            self.stdscr.addstr(height-1, 0, self.status_message[:width-1], curses.color_pair(2))
            self.status_message = ""
        else:
            # Show help
            help_text = {
                ViewMode.LIST: "↑/↓:Navigate Enter:Select t:Tree /:Search q:Quit",
                ViewMode.TREE: "↑/↓:Navigate Enter:Open n:New r:Rename d:Delete m:Move l:List q:Quit",
                ViewMode.SEARCH: "Type:Filter Enter:Apply ESC:Cancel",
                ViewMode.DETAIL: "↑/↓:Scroll q/ESC:Back",
            }.get(self.current_view, "q:Quit")
            self.stdscr.addstr(height-1, 0, help_text[:width-1])
            
        self.stdscr.refresh()
        
    def _draw_list(self) -> None:
        """Draw conversation list."""
        height, width = self.stdscr.getmaxyx()
        view_height = height - 2  # Leave room for title and status
        
        # Title
        title = f"Conversations ({len(self.filtered_conversations)})"
        if self.search_term:
            title += f" - Filter: '{self.search_term}'"
        self.stdscr.addstr(0, 0, title, curses.A_BOLD)
        
        # Adjust offset to keep selection visible
        if self.list_selected < self.list_offset:
            self.list_offset = self.list_selected
        elif self.list_selected >= self.list_offset + view_height:
            self.list_offset = self.list_selected - view_height + 1
            
        # Draw items
        for i in range(view_height):
            idx = self.list_offset + i
            if idx >= len(self.filtered_conversations):
                break
                
            _, conv = self.filtered_conversations[idx]
            is_selected = idx == self.list_selected
            
            # Format line
            timestamp = datetime.fromtimestamp(conv.create_time or 0).strftime("%Y-%m-%d %H:%M")
            max_title_len = width - 20
            title = conv.title[:max_title_len] + "..." if len(conv.title) > max_title_len else conv.title
            line = f"{title:<{max_title_len}} {timestamp}"
            
            # Draw with selection
            attr = curses.color_pair(1) if is_selected else 0
            self.stdscr.addstr(i + 1, 0, line[:width-1], attr)
            
    def _draw_tree(self) -> None:
        """Draw tree view."""
        height, width = self.stdscr.getmaxyx()
        view_height = height - 2
        
        # Title
        folders = sum(1 for n, _, _ in self.tree_items if n.node_type == NodeType.FOLDER)
        convs = sum(1 for n, _, _ in self.tree_items if n.node_type == NodeType.CONVERSATION)
        self.stdscr.addstr(0, 0, f"Tree - {folders} folders, {convs} conversations", curses.A_BOLD)
        
        # Adjust offset
        if self.tree_selected < self.tree_offset:
            self.tree_offset = self.tree_selected
        elif self.tree_selected >= self.tree_offset + view_height:
            self.tree_offset = self.tree_selected - view_height + 1
            
        # Draw items
        for i in range(view_height):
            idx = self.tree_offset + i
            if idx >= len(self.tree_items):
                break
                
            node, conv, depth = self.tree_items[idx]
            is_selected = idx == self.tree_selected
            
            # Build line
            indent = "  " * depth
            if node.node_type == NodeType.FOLDER:
                icon = TREE_CHARS["FOLDER_EXPANDED"] if node.expanded else TREE_CHARS["FOLDER_COLLAPSED"]
                icon += " " + TREE_CHARS["FOLDER_ICON"]
                name = node.name
                attr = curses.color_pair(3) if not is_selected else curses.color_pair(1)
            else:
                icon = TREE_CHARS["CONVERSATION_ICON"]
                name = conv.title if conv else node.name
                attr = curses.color_pair(1) if is_selected else 0
                
            line = f"{indent}{icon} {name}"[:width-1]
            self.stdscr.addstr(i + 1, 0, line, attr)
            
    def _handle_key(self, key: int) -> None:
        """Handle keyboard input."""
        # Mode-specific handling
        if self.current_view == ViewMode.SEARCH:
            result = self.search_view.handle_input(key)
            if result == "search_cancelled":
                self.current_view = ViewMode.LIST
            elif result == "search_submitted":
                self.current_view = ViewMode.LIST
                self.status_message = f"Filter: '{self.search_view.get_search_term()}'"
            return
            
        if self.current_view == ViewMode.DETAIL:
            result = self.detail_view.handle_input(key)
            if result == "close_detail":
                self.current_view = ViewMode.LIST
            return
            
        # Common navigation
        if key == ord('q') or key == 27:  # q or ESC
            self.running = False
        elif key == ord('/'):
            self.current_view = ViewMode.SEARCH
            self.search_view.activate()
        elif key == ord('t') and self.current_view == ViewMode.LIST:
            self.current_view = ViewMode.TREE
        elif key == ord('l') and self.current_view == ViewMode.TREE:
            self.current_view = ViewMode.LIST
            
        # List/Tree navigation
        if self.current_view == ViewMode.LIST:
            self._handle_list_key(key)
        elif self.current_view == ViewMode.TREE:
            self._handle_tree_key(key)
            
    def _handle_list_key(self, key: int) -> None:
        """Handle keys in list view."""
        if not self.filtered_conversations:
            return
            
        if key == curses.KEY_UP:
            self.list_selected = max(0, self.list_selected - 1)
        elif key == curses.KEY_DOWN:
            self.list_selected = min(len(self.filtered_conversations) - 1, self.list_selected + 1)
        elif key == curses.KEY_PPAGE:  # Page Up
            self.list_selected = max(0, self.list_selected - 10)
        elif key == curses.KEY_NPAGE:  # Page Down
            self.list_selected = min(len(self.filtered_conversations) - 1, self.list_selected + 10)
        elif key in (10, 13, curses.KEY_ENTER):  # Enter
            _, conv = self.filtered_conversations[self.list_selected]
            self.detail_view.set_conversation(conv)
            self.current_view = ViewMode.DETAIL
            
    def _handle_tree_key(self, key: int) -> None:
        """Handle keys in tree view."""
        if not self.tree_items:
            return
            
        if key == curses.KEY_UP:
            self.tree_selected = max(0, self.tree_selected - 1)
        elif key == curses.KEY_DOWN:
            self.tree_selected = min(len(self.tree_items) - 1, self.tree_selected + 1)
        elif key in (10, 13, curses.KEY_ENTER, ord(' ')):  # Enter or Space
            node, conv, _ = self.tree_items[self.tree_selected]
            if node.node_type == NodeType.FOLDER:
                node.expanded = not node.expanded
                self._refresh_tree()
            elif conv:
                self.detail_view.set_conversation(conv)
                self.current_view = ViewMode.DETAIL
        elif key == ord('n'):  # New folder
            self._create_folder()
        elif key == ord('r'):  # Rename
            self._rename_item()
        elif key == ord('d'):  # Delete
            self._delete_item()
        elif key == ord('m'):  # Move
            self._move_item()
            
    def _refresh_tree(self) -> None:
        """Refresh tree items."""
        self.tree_items = []
        conversations_map = {c.id: c for c in self.conversations}
        
        def add_items(items: List[Tuple[TreeNode, Optional[Conversation]]], depth: int = 0):
            for node, conv in items:
                self.tree_items.append((node, conv, depth))
                if node.node_type == NodeType.FOLDER and node.expanded and hasattr(node, 'children'):
                    children = []
                    for child_id in node.children:
                        child_node = self.organizer.tree_manager.organization_data.tree_nodes.get(child_id)
                        if child_node:
                            child_conv = conversations_map.get(child_id) if child_node.node_type == NodeType.CONVERSATION else None
                            children.append((child_node, child_conv))
                    children.sort(key=lambda x: (x[0].node_type.value, x[0].name.lower()))
                    add_items(children, depth + 1)
                    
        organized = self.organizer.get_organized_conversations(self.conversations)
        add_items(organized)
        
        # Keep selection in bounds
        if self.tree_selected >= len(self.tree_items):
            self.tree_selected = max(0, len(self.tree_items) - 1)
            
    def _on_search_changed(self, term: str) -> None:
        """Handle search term changes."""
        self.search_term = term.lower()
        if not self.search_term:
            self.filtered_conversations = [(i, c) for i, c in enumerate(self.conversations)]
        else:
            self.filtered_conversations = [
                (i, c) for i, c in enumerate(self.conversations)
                if self.search_term in c.title.lower()
            ]
        self.list_selected = 0
        self.list_offset = 0
        
    def _create_folder(self) -> None:
        """Create new folder."""
        name = get_folder_name_input(self.stdscr, "Folder name:")
        if not name:
            return
            
        try:
            parent_id = None
            if self.tree_selected < len(self.tree_items):
                node, _, _ = self.tree_items[self.tree_selected]
                if node.node_type == NodeType.FOLDER:
                    parent_id = node.id
                    
            self.organizer.create_folder(name, parent_id)
            self._refresh_tree()
            self.status_message = f"Created '{name}'"
        except Exception as e:
            self.status_message = f"Error: {e}"
            
    def _rename_item(self) -> None:
        """Rename selected item."""
        if self.tree_selected >= len(self.tree_items):
            return
            
        node, _, _ = self.tree_items[self.tree_selected]
        new_name = get_folder_name_input(self.stdscr, f"Rename '{node.name}':", node.name)
        if not new_name or new_name == node.name:
            return
            
        try:
            node.name = new_name
            self.organizer.save_organization()
            self._refresh_tree()
            self.status_message = f"Renamed to '{new_name}'"
        except Exception as e:
            self.status_message = f"Error: {e}"
            
    def _delete_item(self) -> None:
        """Delete selected item."""
        if self.tree_selected >= len(self.tree_items):
            return
            
        node, _, _ = self.tree_items[self.tree_selected]
        item_type = "folder" if node.node_type == NodeType.FOLDER else "conversation"
        
        if not confirm_delete(self.stdscr, node.name, item_type):
            return
            
        try:
            self.organizer.tree_manager.delete_node(node.id)
            self.organizer.save_organization()
            self._refresh_tree()
            self.status_message = f"Deleted {item_type}"
        except Exception as e:
            self.status_message = f"Error: {e}"
            
    def _move_item(self) -> None:
        """Move selected item."""
        if self.tree_selected >= len(self.tree_items):
            return
            
        node, _, _ = self.tree_items[self.tree_selected]
        
        # Store current parent to detect cancellation
        current_parent = node.parent_id if hasattr(node, 'parent_id') else None
        
        folder_manager = FolderManager(self.stdscr)
        result = folder_manager.select_folder(self.tree_items, self.tree_selected)
        
        # If select_folder returns None and there are folders to choose from,
        # it means either ESC was pressed or root was selected.
        # We need to check if folders exist to distinguish.
        has_folders = any(n.node_type == NodeType.FOLDER for n, _, _ in self.tree_items)
        
        if result is None and not has_folders:
            # No folders exist, can't move
            self.status_message = "No folders available"
            return
            
        if result == node.id:
            self.status_message = "Cannot move to itself"
            return
            
        # Note: result can be None (root) or a folder ID
        # Both are valid destinations
        try:
            # Check if this is an unorganized conversation (not in tree yet)
            if node.id not in self.organizer.tree_manager.organization_data.tree_nodes:
                # Add it to the tree first
                self.organizer.add_conversation(node.id, result)
            else:
                # It's already in the tree, just move it
                self.organizer.tree_manager.move_node(node.id, result)
            
            self.organizer.save_organization()
            self._refresh_tree()
            self.status_message = f"Moved to {'root' if result is None else 'folder'}"
        except Exception as e:
            self.status_message = f"Error: {e}"


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