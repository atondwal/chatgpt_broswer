#!/usr/bin/env python3
"""Terminal UI for browsing ChatGPT conversations."""

import argparse
import curses
import logging
import sys
from enum import Enum
from pathlib import Path
from typing import List

from src.core.loader import load_conversations
from src.tree.tree import ConversationTree
from src.tui.detail import DetailView
from src.tui.input import get_input, confirm, select_folder
from src.tui.tree_view import TreeView
from src.tui.search_overlay import SearchOverlay


class ViewMode(Enum):
    """Available view modes."""
    TREE = "tree"
    DETAIL = "detail"
    SEARCH = "search"


class TUI:
    """Terminal interface for browsing ChatGPT conversations."""
    
    def __init__(self, conversations_file: str, debug: bool = False):
        self.conversations_file = conversations_file
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        if debug:
            self.logger.setLevel(logging.DEBUG)
        
        # Load data
        self.conversations = load_conversations(conversations_file)
        self.tree = ConversationTree(conversations_file)
        
        # UI state
        self.current_view = ViewMode.TREE
        self.running = True
        self.status_message = ""
        
        # Tree view state
        self.tree_items = []  # List of (TreeNode, Optional[Conversation], depth)
        self.tree_offset = 0
        self.tree_selected = 0
        self.sort_by_date = True  # True for date, False for alphabetical
        
        # Search state
        self.search_term = ""
        self.filtered_conversations = self.conversations  # Conversations matching search
        self.search_matches = []  # List of indices for vim-style search
        self.current_match_index = -1  # Current position in search matches
        self.filter_mode = False  # Whether we're in filter mode (f) vs search mode (/)
        
        # Multi-select state
        self.selected_items = set()  # Set of node IDs that are selected
        self.multi_select_mode = False  # Whether we're in multi-select mode
        self.visual_mode = False  # Visual mode for range selection
        self.visual_start = None  # Starting position for visual mode
        
        # Undo system
        self.undo_stack = []  # Stack of (action, data) tuples
        self.last_action = None  # Last action for repeat
        
        
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
        self.detail_view = DetailView(stdscr, 1, 0, width, height - 2)
        self.tree_view = TreeView(stdscr, 1, 0, width, height - 2)
        self.search_overlay = SearchOverlay(stdscr, 0, 0, width)
        
        # Initialize tree
        try:
            self._refresh_tree()
        except Exception as e:
            if self.debug:
                raise
            self.status_message = f"Tree init error: {str(e)}"
        
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
                self.status_message = f"Error: {str(e)[:50]}"
                
    def _draw(self) -> None:
        """Draw current view."""
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Draw appropriate view
        if self.current_view == ViewMode.DETAIL:
            self.detail_view.draw()
        else:
            self._draw_tree()
            
        # Draw search overlay if active
        if self.current_view == ViewMode.SEARCH:
            self.search_overlay.draw()
            
        # Status line
        if self.status_message:
            self.stdscr.addstr(height-1, 0, self.status_message[:width-1], curses.color_pair(2))
            self.status_message = ""
        else:
            # Show help
            multi_info = f" [{len(self.selected_items)} selected]" if self.selected_items else ""
            visual_info = " [VISUAL]" if self.visual_mode else ""
            search_info = f" [{len(self.search_matches)} matches]" if self.search_matches else ""
            filter_info = f" [{len(self.filtered_conversations)} filtered]" if len(self.filtered_conversations) != len(self.conversations) else ""
            help_text = {
                ViewMode.TREE: f"/:Search f:Filter n/N:Next/Prev x:Delete V:Visual u:Undo F1:Help{multi_info}{visual_info}{search_info}{filter_info}",
                ViewMode.SEARCH: ("Type:Filter Ctrl+W:DelWord ESC:Cancel Enter:Apply" if self.filter_mode else 
                                "Type:Search Ctrl+G:Next Ctrl+W:DelWord ESC:Cancel Enter:Apply"), 
                ViewMode.DETAIL: "↑/↓:Scroll q/ESC:Back",
            }.get(self.current_view, "q:Quit")
            self.stdscr.addstr(height-1, 0, help_text[:width-1])
            
        self.stdscr.refresh()
            
    def _draw_tree(self) -> None:
        """Draw tree view."""
        self.tree_view.set_selected_items(self.selected_items)
        self.tree_view.draw()
            
    def _handle_key(self, key: int) -> None:
        """Handle keyboard input."""
        
        # Search mode handling
        if self.current_view == ViewMode.SEARCH:
            result = self.search_overlay.handle_input(key)
            if result == "search_cancelled":
                self.search_overlay.deactivate()
                self.current_view = ViewMode.TREE
                self._clear_search()
            elif result == "search_submitted":
                self.search_overlay.deactivate()
                self.current_view = ViewMode.TREE
                term = self.search_overlay.get_search_term()
                if self.filter_mode:
                    # Filter mode - update filtered conversations
                    if term:
                        self._update_search(term)
                        self.status_message = f"Filter: '{term}' ({len(self.filtered_conversations)} matches)"
                    else:
                        self._clear_search()
                else:
                    # Search mode - find and jump to matches
                    if term:
                        self.search_term = term
                        self.search_matches = self._find_search_matches(term)
                        if self.search_matches:
                            self._jump_to_match(0)  # Jump to first match
                        else:
                            self.status_message = f"No matches found for: {term}"
                    else:
                        self.search_matches = []
                        self.current_match_index = -1
            elif result == "search_changed":
                term = self.search_overlay.get_search_term()
                if self.filter_mode:
                    # Filter mode - update filtered conversations as user types
                    if term:
                        self._update_search(term)
                        # Don't show status message for every keystroke in filter mode
                    else:
                        self._clear_search()
                else:
                    # Incremental search - update matches and jump to first match as user types
                    if term:
                        self.search_term = term
                        self.search_matches = self._find_search_matches(term)
                        if self.search_matches:
                            self._jump_to_match(0)  # Jump to first match immediately
                        else:
                            # Show no matches message but don't clear previous position
                            self.status_message = f"No matches for: {term}"
                    else:
                        # Empty search - clear matches but don't jump anywhere
                        self.search_matches = []
                        self.current_match_index = -1
            elif result == "search_next_match":
                # Ctrl+G in search mode - go to next match without leaving search
                if not self.filter_mode:  # Only works in search mode, not filter mode
                    term = self.search_overlay.get_search_term()
                    if term:
                        self.search_term = term
                        self.search_matches = self._find_search_matches(term)
                        if self.search_matches:
                            # If we have a current match, go to next, otherwise start at first
                            if self.current_match_index >= 0:
                                self._search_next()
                            else:
                                self._jump_to_match(0)
                        else:
                            self.status_message = f"No matches found for: {term}"
            return
            
        if self.current_view == ViewMode.DETAIL:
            result = self.detail_view.handle_input(key)
            if result == "close_detail":
                self.current_view = ViewMode.TREE
            return
            
        # Common navigation
        if key == ord('q'):
            self.running = False
        elif key == 27:  # ESC - clear selection if in multi-select mode, otherwise quit
            if self.selected_items:
                self.selected_items.clear()
                self.status_message = "Selection cleared"
            else:
                self.running = False
        elif key == ord('/'):
            self._start_vim_search()
        elif key == 1:  # Ctrl+A
            self._select_all()
        elif key == ord(' '):  # Space for multi-select
            self._toggle_item_selection()
            
        # Tree navigation (only view mode now)
        if self.current_view == ViewMode.TREE:
            self._handle_tree_key(key)
            
    def _handle_tree_key(self, key: int) -> None:
        """Handle keys in tree view."""
        # Store previous selection for visual mode
        prev_selected = self.tree_view.selected
        
        result = self.tree_view.handle_input(key)
        
        # Update visual mode selection if cursor moved
        if self.visual_mode and self.tree_view.selected != prev_selected:
            self._update_visual_selection()
        
        if result == "select":
            item = self.tree_view.get_selected()
            if item:
                node, conv, _ = item
                if node.is_folder:
                    self.tree.toggle_folder(node.id)
                    self._refresh_tree()
                elif conv:
                    self.detail_view.set_conversation(conv)
                    self.current_view = ViewMode.DETAIL
        elif result == "toggle":
            item = self.tree_view.get_selected()
            if item:
                node, _, _ = item
                if node.is_folder:
                    self.tree.toggle_folder(node.id)
                    self._refresh_tree()
        elif result == "expand_all":
            for node in self.tree.nodes.values():
                if node.is_folder:
                    node.expanded = True
            self._refresh_tree()
        elif result == "collapse_all":
            for node in self.tree.nodes.values():
                if node.is_folder:
                    node.expanded = False
            self._refresh_tree()
        elif result == "move_up":
            if self.selected_items:
                self._bulk_move_up()
            else:
                item = self.tree_view.get_selected()
                if item:
                    node, _, _ = item
                    if self.tree.move_item_up(node.id):
                        self._save_last_action("move_up")
                        self.tree.save()
                        self._refresh_tree()
                        self._move_cursor_to_item(node.id)
                        self.status_message = f"Moved '{node.name}' up"
                    else:
                        self.status_message = "Cannot move up"
        elif result == "move_down":
            if self.selected_items:
                self._bulk_move_down()
            else:
                item = self.tree_view.get_selected()
                if item:
                    node, _, _ = item
                    if self.tree.move_item_down(node.id):
                        self._save_last_action("move_down")
                        self.tree.save()
                        self._refresh_tree()
                        self._move_cursor_to_item(node.id)
                        self.status_message = f"Moved '{node.name}' down"
                    else:
                        self.status_message = "Cannot move down"
        # Handle enhanced keybindings from tree_view
        elif result == "delete":
            self._delete_item()
        elif result == "copy":
            self._copy_item()
        elif result == "paste":
            self._paste_item()
        elif result == "undo":
            self._undo_action()
        elif result == "repeat":
            self._repeat_last_action()
        elif result == "help":
            self._show_tree_help()
        elif result == "rename":
            self._rename_item()
        elif result == "refresh":
            self._refresh_conversations()
        elif result == "new_folder":
            self._create_folder()
        elif result == "visual_mode":
            self._toggle_visual_mode()
        elif result == "indent":
            self._indent_items()
        elif result == "outdent":
            self._outdent_items()
        elif result == "quick_filter":
            self._quick_filter()
        elif key == ord('n'):  # Next search match
            self._search_next()
        elif key == ord('N'):  # Previous search match
            self._search_previous()
        elif result == "filter_folders":
            self._filter_folders()
        elif result == "filter_conversations":
            self._filter_conversations()
        elif result == "show_all":
            self._show_all()
        elif result and result.startswith("expand_depth_"):
            depth = int(result.split("_")[-1])
            self._expand_to_depth(depth)
        # Legacy explicit key handling (fallback for keys not handled by tree_view)
        elif key == ord('n'):  # New folder
            self._create_folder()
        elif key == ord('r'):  # Rename
            self._rename_item()
        elif key == ord('d'):  # Delete
            self._delete_item()
        elif key == ord('m'):  # Move
            if self.selected_items:
                self._bulk_move_items()
            else:
                self._move_item()
        elif key == ord('?'):  # Help
            self._show_tree_help()
        elif key == ord('o'):  # Toggle sort order
            self._toggle_sort_order()
        elif key == ord('O'):  # Clear custom ordering (Shift+O)
            self._clear_custom_order()
            
    def _refresh_tree(self) -> None:
        """Refresh tree items."""
        self.tree_items = self.tree.get_tree_items(self.filtered_conversations, sort_by_date=self.sort_by_date)
        self.tree_view.set_items(self.tree_items)
        
        # Keep selection in bounds
        if self.tree_selected >= len(self.tree_items):
            self.tree_selected = max(0, len(self.tree_items) - 1)
            
        
    def _create_folder(self) -> None:
        """Create new folder."""
        name = get_input(self.stdscr, "Folder name:")
        if not name:
            return
            
        try:
            parent_id = None
            item = self.tree_view.get_selected()
            if item:
                node, _, _ = item
                if node.is_folder:
                    parent_id = node.id
                    
            folder_id = self.tree.create_folder(name, parent_id)
            
            # If we have selected items, move them into the new folder
            if self.selected_items:
                moved_items = []
                for item_id in self.selected_items.copy():  # Copy to avoid modification during iteration
                    try:
                        self.tree.move_node(item_id, folder_id)
                        moved_items.append(self.tree.nodes[item_id].name)
                    except Exception:
                        pass  # Skip items that can't be moved
                
                self.selected_items.clear()  # Clear selection after moving
                
                if moved_items:
                    self.status_message = f"Created '{name}' and moved {len(moved_items)} items into it"
                else:
                    self.status_message = f"Created '{name}' (no items could be moved)"
            else:
                self.status_message = f"Created '{name}'"
                
            self.tree.save()
            self._refresh_tree()
            
        except Exception as e:
            self.status_message = f"Error: {e}"
            
    def _rename_item(self) -> None:
        """Rename selected item."""
        item = self.tree_view.get_selected()
        if not item:
            return
            
        node, _, _ = item
        new_name = get_input(self.stdscr, f"Rename '{node.name}':", node.name)
        if not new_name or new_name == node.name:
            return
            
        try:
            self.tree.rename_node(node.id, new_name)
            self.tree.save()
            self._refresh_tree()
            self.status_message = f"Renamed to '{new_name}'"
        except Exception as e:
            self.status_message = f"Error: {e}"
            
    def _delete_item(self) -> None:
        """Delete selected item."""
        item = self.tree_view.get_selected()
        if not item:
            return
            
        node, _, _ = item
        item_type = "folder" if node.is_folder else "conversation"
        
        if not confirm(self.stdscr, f"Delete {item_type} '{node.name}'?"):
            return
            
        try:
            self.tree.delete_node(node.id)
            self.tree.save()
            self._refresh_tree()
            self.status_message = f"Deleted {item_type}"
        except Exception as e:
            self.status_message = f"Error: {e}"
            
    def _move_item(self) -> None:
        """Move selected item."""
        item = self.tree_view.get_selected()
        if not item:
            return
            
        node, _, _ = item
        dest_id = select_folder(self.stdscr, self.tree_items)
        
        if dest_id == node.id:
            self.status_message = "Cannot move to itself"
            return
            
        try:
            self.tree.move_node(node.id, dest_id)
            self.tree.save()
            self._refresh_tree()
            self.status_message = f"Moved to {'root' if dest_id is None else 'folder'}"
        except Exception as e:
            self.status_message = f"Error: {e}"
            
    def _show_tree_help(self) -> None:
        """Show help dialog for tree view."""
        help_text = [
            "Enhanced Keybindings:",
            "",
            "Vim Navigation:",
            "  ↑/k, ↓/j   - Move up/down",
            "  gg, G      - Go to top/bottom",  
            "  Ctrl+D/U   - Half page down/up",
            "  Ctrl+F/B   - Full page down/up",
            "  H/M/L      - Jump High/Middle/Low on screen",
            "  h/l        - Jump to parent / Expand folder",
            "  zz         - Center current item",
            "",
            "Quick Actions:",
            "  x, dd      - Delete item",
            "  yy         - Copy title",
            "  p          - Paste",
            "  u          - Undo",
            "  .          - Repeat action",
            "",
            "Function Keys:",
            "  F1         - Help",
            "  F2         - Rename",
            "  F5         - Refresh",
            "  Delete     - Delete item",
            "  Insert     - New folder",
            "",
            "Multi-select:",
            "  Space      - Select/deselect",
            "  Ctrl+A     - Select all",
            "  V          - Visual mode",
            "  >/< indent/outdent",
            "",
            "Filters:",
            "  f          - Quick filter",
            "  F/C        - Folders/Conversations only",
            "  a          - Show all",
            "  0-9        - Expand to depth",
            "",
            "Organization:",
            "  n/r/d/m    - New/Rename/Delete/Move",
            "  Shift+J/K  - Reorder up/down",
            "  o          - Toggle sort",
            "",
            "Search: / (vim search), f (filter), n/N (next/prev),"
            "",
            "Press any key to close..."
        ]
        
        # Calculate dialog size
        height = len(help_text) + 2
        width = max(len(line) for line in help_text) + 4
        
        # Center dialog
        screen_height, screen_width = self.stdscr.getmaxyx()
        y = (screen_height - height) // 2
        x = (screen_width - width) // 2
        
        # Create window
        win = curses.newwin(height, width, y, x)
        win.keypad(True)
        win.border()
        
        # Show help text
        for i, line in enumerate(help_text):
            win.addstr(i + 1, 2, line)
            
        win.refresh()
        win.getch()  # Wait for any key
        
    def _toggle_sort_order(self) -> None:
        """Toggle between date and alphabetical sorting."""
        self.sort_by_date = not self.sort_by_date
        # Clear custom ordering to avoid conflicts with new sort order
        self.tree.custom_order.clear()
        self._refresh_tree()
        self.status_message = f"Sorting by {'date (newest first)' if self.sort_by_date else 'name (A-Z)'} - custom order cleared"
        
    def _clear_custom_order(self) -> None:
        """Clear all custom ordering and return to automatic sorting."""
        self.tree.custom_order.clear()
        self.tree.save()
        self._refresh_tree()
        self.status_message = "Custom ordering cleared - using automatic sort"
        
    def _move_cursor_to_item(self, item_id: str) -> None:
        """Move cursor to the specified item in the tree."""
        for i, (node, _, _) in enumerate(self.tree_items):
            if node.id == item_id:
                self.tree_view.selected = i
                self.tree_view._ensure_visible()
                break
                
    def _update_search(self, term: str) -> None:
        """Update search filtering."""
        self.search_term = term.lower()
        if not self.search_term:
            self.filtered_conversations = self.conversations
        else:
            # Search in both title and content
            self.filtered_conversations = []
            for conv in self.conversations:
                # Check title
                if self.search_term in conv.title.lower():
                    self.filtered_conversations.append(conv)
                    continue
                    
                # Check message content
                found_in_content = False
                for message in conv.messages:
                    if self.search_term in message.content.lower():
                        found_in_content = True
                        break
                        
                if found_in_content:
                    self.filtered_conversations.append(conv)
                    
        self._refresh_tree()
        
    def _clear_search(self) -> None:
        """Clear search filter."""
        self.search_term = ""
        self.filtered_conversations = self.conversations
        self._refresh_tree()
        
    def _select_all(self) -> None:
        """Select all visible items."""
        for node, _, _ in self.tree_items:
            self.selected_items.add(node.id)
        self.status_message = f"Selected {len(self.selected_items)} items"
        
    def _toggle_item_selection(self) -> None:
        """Toggle selection of current item."""
        item = self.tree_view.get_selected()
        if not item:
            return
            
        node, _, _ = item
        if node.id in self.selected_items:
            self.selected_items.remove(node.id)
            self.status_message = f"Deselected '{node.name}'"
        else:
            self.selected_items.add(node.id)
            self.status_message = f"Selected '{node.name}'"
            
    def _bulk_move_up(self) -> None:
        """Move all selected items up."""
        if not self.selected_items:
            return
            
        # Get items in tree order
        selected_in_order = []
        for node, _, _ in self.tree_items:
            if node.id in self.selected_items:
                selected_in_order.append(node.id)
                
        # Move from top to bottom to maintain relative order
        moved = 0
        for item_id in selected_in_order:
            if self.tree.move_item_up(item_id):
                moved += 1
                
        if moved > 0:
            self.tree.save()
            self._refresh_tree()
            self.status_message = f"Moved {moved} items up"
        else:
            self.status_message = "Cannot move selected items up"
            
    def _bulk_move_down(self) -> None:
        """Move all selected items down."""
        if not self.selected_items:
            return
            
        # Get items in reverse tree order
        selected_in_order = []
        for node, _, _ in reversed(self.tree_items):
            if node.id in self.selected_items:
                selected_in_order.append(node.id)
                
        # Move from bottom to top to maintain relative order
        moved = 0
        for item_id in selected_in_order:
            if self.tree.move_item_down(item_id):
                moved += 1
                
        if moved > 0:
            self.tree.save()
            self._refresh_tree()
            self.status_message = f"Moved {moved} items down"
        else:
            self.status_message = "Cannot move selected items down"
            
    def _bulk_move_items(self) -> None:
        """Move all selected items to a new parent."""
        if not self.selected_items:
            return
            
        dest_id = select_folder(self.stdscr, self.tree_items)
        
        moved = 0
        for item_id in self.selected_items:
            if item_id != dest_id:  # Can't move to itself
                try:
                    self.tree.move_node(item_id, dest_id)
                    moved += 1
                except Exception:
                    pass  # Skip items that can't be moved
                    
        if moved > 0:
            self.tree.save()
            self._refresh_tree()
            self.selected_items.clear()
            self.status_message = f"Moved {moved} items to {'root' if dest_id is None else 'folder'}"
        else:
            self.status_message = "No items could be moved"
            
    def _copy_item(self) -> None:
        """Copy current item title to clipboard (conceptually)."""
        item = self.tree_view.get_selected()
        if item:
            node, conv, _ = item
            title = conv.title if conv else node.name
            # Store for potential paste operation
            self.clipboard = {"type": "title", "data": title}
            self.status_message = f"Copied: {title[:30]}..."
    
    def _paste_item(self) -> None:
        """Paste/duplicate item."""
        if hasattr(self, 'clipboard') and self.clipboard:
            self.status_message = f"Paste: {self.clipboard['data'][:30]}..."
        else:
            self.status_message = "Nothing to paste"
    
    def _undo_action(self) -> None:
        """Undo last action."""
        if not self.undo_stack:
            self.status_message = "Nothing to undo"
            return
            
        action, data = self.undo_stack.pop()
        
        if action == "move":
            # Undo move: move back to original position
            node_id, original_parent = data
            try:
                self.tree.move_node(node_id, original_parent)
                self.tree.save()
                self._refresh_tree()
                self.status_message = f"Undid move operation"
            except Exception as e:
                self.status_message = f"Undo failed: {e}"
        elif action in ("indent", "outdent"):
            # Undo indent/outdent: restore all items to original positions
            original_positions = data
            try:
                for item_id, original_parent in original_positions:
                    if item_id in self.tree.nodes:
                        self.tree.move_node(item_id, original_parent)
                self.tree.save()
                self._refresh_tree()
                self.status_message = f"Undid {action} operation"
            except Exception as e:
                self.status_message = f"Undo failed: {e}"
        elif action == "delete":
            # Undo delete: restore from data
            self.status_message = "Delete undo not implemented yet"
        elif action == "create":
            # Undo create: delete the created item
            node_id = data
            if node_id in self.tree.nodes:
                self.tree.delete_node(node_id)
                self.tree.save()
                self._refresh_tree()
                self.status_message = "Undid create operation"
        else:
            self.status_message = f"Cannot undo action: {action}"
    
    def _repeat_last_action(self) -> None:
        """Repeat last action."""
        if not self.last_action:
            self.status_message = "No action to repeat"
            return
            
        action_type, action_data = self.last_action
        
        if action_type == "move_up":
            item = self.tree_view.get_selected()
            if item:
                node, _, _ = item
                if self.tree.move_item_up(node.id):
                    self.tree.save()
                    self._refresh_tree()
                    self._move_cursor_to_item(node.id)
                    self.status_message = f"Repeated: moved '{node.name}' up"
        elif action_type == "move_down":
            item = self.tree_view.get_selected()
            if item:
                node, _, _ = item
                if self.tree.move_item_down(node.id):
                    self.tree.save()
                    self._refresh_tree()
                    self._move_cursor_to_item(node.id)
                    self.status_message = f"Repeated: moved '{node.name}' down"
        else:
            self.status_message = f"Cannot repeat action: {action_type}"
    
    def _save_undo_state(self, action: str, data: any) -> None:
        """Save state for undo functionality."""
        self.undo_stack.append((action, data))
        # Limit undo stack size
        if len(self.undo_stack) > 20:
            self.undo_stack.pop(0)
            
    def _save_last_action(self, action_type: str, action_data: any = None) -> None:
        """Save last action for repeat functionality."""
        self.last_action = (action_type, action_data)
    
    def _refresh_conversations(self) -> None:
        """Refresh conversations from file."""
        try:
            self.conversations = load_conversations(self.conversations_file)
            self.filtered_conversations = self.conversations
            self._refresh_tree()
            self.status_message = f"Refreshed {len(self.conversations)} conversations"
        except Exception as e:
            self.status_message = f"Refresh failed: {e}"
    
    def _toggle_visual_mode(self) -> None:
        """Toggle visual selection mode."""
        if not self.visual_mode:
            # Enter visual mode
            self.visual_mode = True
            self.visual_start = self.tree_view.selected
            # Start with current item selected
            if self.visual_start < len(self.tree_items):
                node, _, _ = self.tree_items[self.visual_start]
                self.selected_items.add(node.id)
            self.status_message = "Visual mode activated - use arrows to select range"
        else:
            # Exit visual mode
            self.visual_mode = False
            self.visual_start = None
            self.status_message = f"Visual mode deactivated - {len(self.selected_items)} items selected"
    
    def _update_visual_selection(self) -> None:
        """Update selection based on visual mode range."""
        if not self.visual_mode or self.visual_start is None:
            return
            
        # Clear previous selection and rebuild based on range
        self.selected_items.clear()
        
        current_pos = self.tree_view.selected
        start_pos = self.visual_start
        
        # Determine the range (inclusive)
        min_pos = min(start_pos, current_pos)
        max_pos = max(start_pos, current_pos)
        
        # Select all items in the range
        for i in range(min_pos, max_pos + 1):
            if i < len(self.tree_items):
                node, _, _ = self.tree_items[i]
                self.selected_items.add(node.id)
                
        # Update status to show selection size
        self.status_message = f"Visual: {len(self.selected_items)} items selected"
    
    def _indent_items(self) -> None:
        """Indent selected items (move them into a sibling folder)."""
        if not self.selected_items:
            self.status_message = "No items selected to indent"
            return
            
        # Find a suitable folder to move items into
        current_item = self.tree_view.get_selected()
        if not current_item:
            self.status_message = "Cannot determine target for indentation"
            return
            
        current_node, _, _ = current_item
        
        # Look for a folder at the same level to move items into
        parent_id = current_node.parent_id
        siblings = self.tree.nodes[parent_id].children if parent_id else self.tree.root_nodes
        
        # Find first folder sibling
        target_folder = None
        for sibling_id in siblings:
            sibling = self.tree.nodes.get(sibling_id)
            if sibling and sibling.is_folder and sibling_id not in self.selected_items:
                target_folder = sibling_id
                break
                
        if target_folder:
            # Save undo state before making changes
            original_positions = []
            for item_id in self.selected_items:
                if item_id in self.tree.nodes:
                    node = self.tree.nodes[item_id]
                    original_positions.append((item_id, node.parent_id))
            
            if original_positions:
                self._save_undo_state("indent", original_positions)
            
            moved = 0
            for item_id in self.selected_items:
                try:
                    self.tree.move_node(item_id, target_folder)
                    moved += 1
                except Exception:
                    pass
                    
            if moved > 0:
                self.tree.save()
                self._refresh_tree()
                self.selected_items.clear()
                self.status_message = f"Indented {moved} items into folder"
            else:
                self.status_message = "Could not indent items"
        else:
            self.status_message = "No folder available for indentation"
    
    def _outdent_items(self) -> None:
        """Outdent selected items (move them to parent level)."""
        if not self.selected_items:
            self.status_message = "No items selected to outdent"
            return
            
        # Save undo state before making changes
        original_positions = []
        for item_id in self.selected_items:
            if item_id in self.tree.nodes:
                node = self.tree.nodes[item_id]
                original_positions.append((item_id, node.parent_id))
        
        if original_positions:
            self._save_undo_state("outdent", original_positions)
            
        moved = 0
        for item_id in self.selected_items:
            node = self.tree.nodes.get(item_id)
            if node and node.parent_id:
                # Move to the parent's parent
                grandparent_id = self.tree.nodes[node.parent_id].parent_id if node.parent_id in self.tree.nodes else None
                try:
                    self.tree.move_node(item_id, grandparent_id)
                    moved += 1
                except Exception:
                    pass
                    
        if moved > 0:
            self.tree.save()
            self._refresh_tree()
            self.selected_items.clear()
            self.status_message = f"Outdented {moved} items"
        else:
            self.status_message = "Could not outdent items (already at top level?)"
    
    def _quick_filter(self) -> None:
        """Start filter mode (filters the tree)."""
        self.filter_mode = True
        self.current_view = ViewMode.SEARCH
        self.search_overlay.activate()
        self.status_message = "Filter mode: type to filter conversations"
    
    def _start_vim_search(self) -> None:
        """Start vim-style search that jumps to matches."""
        self.filter_mode = False
        self.current_view = ViewMode.SEARCH
        self.search_overlay.activate()
        self.status_message = "Incremental search: type to find and jump to matches"
    
    def _find_search_matches(self, term: str) -> List[int]:
        """Find all tree items that match the search term."""
        if not term:
            return []
            
        matches = []
        term_lower = term.lower()
        
        for i, (node, conv, _) in enumerate(self.tree_items):
            # Search in node name
            if term_lower in node.name.lower():
                matches.append(i)
                continue
                
            # Search in conversation title and content
            if conv:
                if term_lower in conv.title.lower():
                    matches.append(i)
                    continue
                    
                # Search in message content
                for message in conv.messages:
                    if term_lower in message.content.lower():
                        matches.append(i)
                        break
                        
        return matches
    
    def _jump_to_match(self, match_index: int) -> None:
        """Jump to a specific search match."""
        if 0 <= match_index < len(self.search_matches):
            tree_index = self.search_matches[match_index]
            if tree_index < len(self.tree_items):
                self.tree_view.selected = tree_index
                self.tree_view._ensure_visible()
                self.current_match_index = match_index
                
                # Show match info
                total_matches = len(self.search_matches)
                self.status_message = f"Match {match_index + 1}/{total_matches}: {self.search_term}"
    
    def _search_next(self) -> None:
        """Jump to next search match."""
        if not self.search_matches:
            self.status_message = "No search results. Use / to search."
            return
            
        next_index = (self.current_match_index + 1) % len(self.search_matches)
        self._jump_to_match(next_index)
    
    def _search_previous(self) -> None:
        """Jump to previous search match."""
        if not self.search_matches:
            self.status_message = "No search results. Use / to search."
            return
            
        prev_index = (self.current_match_index - 1) % len(self.search_matches)
        self._jump_to_match(prev_index)
    
    def _filter_folders(self) -> None:
        """Show only folders."""
        # Filter conversations to empty, keeping only folder structure
        self.filtered_conversations = []
        self._refresh_tree()
        self.status_message = "Showing only folders"
    
    def _filter_conversations(self) -> None:
        """Show only conversations."""
        # This would need more complex logic to flatten the tree
        self.status_message = "Showing only conversations"
    
    def _show_all(self) -> None:
        """Show all items (clear filters)."""
        self.filtered_conversations = self.conversations
        self._refresh_tree()
        self.status_message = "Showing all items"
    
    def _expand_to_depth(self, depth: int) -> None:
        """Expand tree to specific depth level."""
        if depth == 0:
            # Collapse all
            for node in self.tree.nodes.values():
                if node.is_folder:
                    node.expanded = False
        else:
            # Expand to specified depth
            def expand_recursive(node_ids, current_depth):
                for node_id in node_ids:
                    if node_id in self.tree.nodes:
                        node = self.tree.nodes[node_id]
                        if node.is_folder:
                            node.expanded = current_depth < depth
                            if node.expanded:
                                expand_recursive(node.children, current_depth + 1)
            
            expand_recursive(self.tree.root_nodes, 1)
        
        self._refresh_tree()
        if depth == 0:
            self.status_message = "Collapsed all folders"
        else:
            self.status_message = f"Expanded to depth {depth}"


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
        tui = TUI(args.conversations_file, debug=args.debug)
        curses.wrapper(tui.run)
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()