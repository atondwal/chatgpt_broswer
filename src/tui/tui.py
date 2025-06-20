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
from src.core.claude_loader import find_claude_project_for_cwd, list_claude_projects
from src.core.exporter import export_conversation as export_conv
from src.tree.tree import ConversationTree
from src.tui.input import get_input, confirm, select_folder
from src.tui.tree_view import TreeView
from src.tui.search_overlay import SearchOverlay
from src.tui.selection_manager import SelectionManager
from src.tui.search_manager import SearchManager
from src.tui.operations_manager import OperationsManager
from src.tui.action_manager import ActionManager
from src.tui.tree_manager import TreeManager
from src.tui.action_handler import ActionContext, ActionResult


class ViewMode(Enum):
    """Available view modes."""
    TREE = "tree"
    SEARCH = "search"


class TUI:
    """Terminal interface for browsing ChatGPT conversations."""
    
    def __init__(self, conversations_file: str, debug: bool = False, format: str = "auto"):
        self.conversations_file = conversations_file
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        if debug:
            self.logger.setLevel(logging.DEBUG)
        
        # Load data
        self.conversations = load_conversations(conversations_file, format=format)
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
        
        # Search state (keeping some here for compatibility)
        self.search_term = ""
        self.filtered_conversations = self.conversations  # Conversations matching search
        
        # Initialize managers
        self.selection_manager = SelectionManager()
        self.search_manager = SearchManager()
        self.action_manager = ActionManager()
        # Note: operations_manager and tree_manager need stdscr/tui, so we'll initialize them in run()
        
        # Action handlers list (will be populated in run())
        self.action_handlers = []
        
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
        self.tree_view = TreeView(stdscr)
        height, width = stdscr.getmaxyx()
        self.search_overlay = SearchOverlay(stdscr, 0, 0, width)
        self.operations_manager = OperationsManager(self.tree, stdscr)
        self.tree_manager = TreeManager(self.tree, self)
        
        # Register action handlers in order of priority
        self.action_handlers = [
            self.tree_manager,       # Tree operations (expand/collapse, etc.)
            self.operations_manager,  # CRUD operations
            self.selection_manager,   # Selection and visual mode
            self.search_manager,      # Search functionality
            self.action_manager,      # Undo/redo/copy/paste
        ]
        
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
                # Use enhanced key reading for better function key support
                from src.tui.key_mapper import get_key_with_escape_handling
                key = get_key_with_escape_handling(stdscr)
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
        
        # Draw tree view
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
            multi_info = f" [{len(self.selection_manager.selected_items)} selected]" if self.selection_manager.selected_items else ""
            visual_info = " [VISUAL]" if self.selection_manager.visual_mode else ""
            search_info = f" [{len(self.search_manager.search_matches)} matches]" if self.search_manager.search_matches else ""
            filter_info = f" [{len(self.filtered_conversations)} filtered]" if len(self.filtered_conversations) != len(self.conversations) else ""
            help_text = {
                ViewMode.TREE: f"/:Search f:Filter n/N:Next/Prev x:Delete V:Visual u:Undo F1:Help{multi_info}{visual_info}{search_info}{filter_info}",
                ViewMode.SEARCH: ("Type:Filter Ctrl+W:DelWord ESC:Cancel Enter:Apply" if self.search_manager.filter_mode else 
                                "Type:Search Ctrl+G:Next Ctrl+W:DelWord ESC:Cancel Enter:Apply"), 
            }.get(self.current_view, "q:Quit")
            self.stdscr.addstr(height-1, 0, help_text[:width-1])
            
        self.stdscr.refresh()
            
    def _draw_tree(self) -> None:
        """Draw tree view."""
        self.tree_view.set_selected_items(self.selection_manager.selected_items)
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
                if self.search_manager.is_filter_mode():
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
                        self.search_manager.search_matches = self.search_manager.find_search_matches(term, self.tree_items)
                        if self.search_manager.search_matches:
                            tree_index, status = self.search_manager.jump_to_match(0)
                            if tree_index is not None and tree_index < len(self.tree_items):
                                self.tree_view.selected = tree_index
                                self.tree_view._ensure_visible()
                                self.status_message = status
                        else:
                            self.status_message = f"No matches found for: {term}"
                    else:
                        self.search_manager.search_matches = []
                        self.search_manager.current_match_index = -1
            elif result == "search_changed":
                term = self.search_overlay.get_search_term()
                if self.search_manager.is_filter_mode():
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
                        self.search_manager.search_matches = self.search_manager.find_search_matches(term, self.tree_items)
                        if self.search_manager.search_matches:
                            tree_index, status = self.search_manager.jump_to_match(0)
                            if tree_index is not None and tree_index < len(self.tree_items):
                                self.tree_view.selected = tree_index
                                self.tree_view._ensure_visible()
                                self.status_message = status
                        else:
                            # Show no matches message but don't clear previous position
                            self.status_message = f"No matches for: {term}"
                    else:
                        # Empty search - clear matches but don't jump anywhere
                        self.search_manager.search_matches = []
                        self.search_manager.current_match_index = -1
            elif result == "search_next_match":
                # Ctrl+G in search mode - go to next match without leaving search
                if not self.search_manager.is_filter_mode():  # Only works in search mode, not filter mode
                    term = self.search_overlay.get_search_term()
                    if term:
                        self.search_term = term
                        self.search_manager.search_matches = self.search_manager.find_search_matches(term, self.tree_items)
                        if self.search_manager.search_matches:
                            # If we have a current match, go to next, otherwise start at first
                            if self.search_manager.current_match_index >= 0:
                                tree_index, status = self.search_manager.search_next()
                                if tree_index is not None:
                                    self.tree_view.selected = tree_index
                                    self.tree_view._ensure_visible()
                                self.status_message = status
                            else:
                                tree_index, status = self.search_manager.jump_to_match(0)
                                if tree_index is not None and tree_index < len(self.tree_items):
                                    self.tree_view.selected = tree_index
                                    self.tree_view._ensure_visible()
                                    self.status_message = status
                        else:
                            self.status_message = f"No matches found for: {term}"
            return
            
            
        # Common navigation
        if key == ord('q'):
            self.running = False
        elif key == 27:  # ESC - clear selection if in multi-select mode, otherwise quit
            if self.selection_manager.selected_items:
                self.status_message = self.selection_manager.clear_selection()
            else:
                self.running = False
        elif key == ord('/'):
            self._start_vim_search()
        elif key == 1:  # Ctrl+A
            count = self.selection_manager.select_all(self.tree_items)
            self.status_message = f"Selected {count} items"
        elif key == ord(' '):  # Space for multi-select
            item = self.tree_view.get_selected()
            if item:
                node, _, _ = item
                _, self.status_message = self.selection_manager.toggle_item_selection(node.id, node.name)
            
        # Tree navigation (only view mode now)
        if self.current_view == ViewMode.TREE:
            self._handle_tree_key(key)
            
    def _handle_tree_key(self, key: int) -> None:
        """Handle keys in tree view."""
        # Store previous selection for visual mode
        prev_selected = self.tree_view.selected
        
        result = self.tree_view.handle_input(key)
        
        # Update visual mode selection if cursor moved
        if self.selection_manager.visual_mode and self.tree_view.selected != prev_selected:
            self.status_message = self.selection_manager.update_visual_selection(
                self.tree_view.selected, self.tree_items
            )
        
        # If tree_view handled the input and produced a result
        if result:
            # Create action context
            context = ActionContext(self, key, result)
            
            # Let each handler process the action
            for handler in self.action_handlers:
                if handler.can_handle(result):
                    action_result = handler.handle(result, context)
                    if action_result:
                        # Process action result
                        if action_result.message:
                            self.status_message = action_result.message
                        if action_result.save_tree:
                            self.tree.save()
                        if action_result.refresh_tree:
                            self._refresh_tree()
                        if action_result.change_view:
                            self.current_view = action_result.change_view
                        if action_result.clear_selection:
                            self.selection_manager.clear_selection()
                        break
                        
        # Handle special search keys that don't come as results from tree_view
        if key == ord('n') and not result:  # Next search match
            context = ActionContext(self, key, "search_next")
            action_result = self.search_manager.handle("search_next", context)
            if action_result:
                self.status_message = action_result.message
        elif key == ord('N') and not result:  # Previous search match
            context = ActionContext(self, key, "search_previous")
            action_result = self.search_manager.handle("search_previous", context)
            if action_result:
                self.status_message = action_result.message
                
        # Handle special cases that need UI interaction
        elif result == "quick_filter":
            self._quick_filter()
            
        # Legacy key handling for keys not converted to results yet
        elif not result:
            self._handle_legacy_key(key)
            
    def _handle_legacy_key(self, key: int) -> None:
        """Handle legacy key bindings not yet converted to action results."""
        if key == ord('o'):  # Toggle sort order
            context = ActionContext(self, key, "toggle_sort")
            action_result = self.tree_manager.handle("toggle_sort", context)
            if action_result:
                self.status_message = action_result.message
                if action_result.refresh_tree:
                    self._refresh_tree()
        elif key == ord('O'):  # Clear custom ordering
            context = ActionContext(self, key, "clear_custom_order")
            action_result = self.tree_manager.handle("clear_custom_order", context)
            if action_result:
                self.status_message = action_result.message
                if action_result.save_tree:
                    self.tree.save()
                if action_result.refresh_tree:
                    self._refresh_tree()
        elif key == ord('n'):  # New folder (legacy)
            context = ActionContext(self, key, "new_folder")
            action_result = self.operations_manager.handle("new_folder", context)
            if action_result:
                self.status_message = action_result.message
                if action_result.save_tree:
                    self.tree.save()
                if action_result.refresh_tree:
                    self._refresh_tree()
                if action_result.clear_selection:
                    self.selection_manager.clear_selection()
        elif key == ord('r'):  # Rename
            context = ActionContext(self, key, "rename")
            action_result = self.operations_manager.handle("rename", context)
            if action_result:
                self.status_message = action_result.message
                if action_result.save_tree:
                    self.tree.save()
                if action_result.refresh_tree:
                    self._refresh_tree()
        elif key == ord('d'):  # Delete
            context = ActionContext(self, key, "delete")
            action_result = self.operations_manager.handle("delete", context)
            if action_result:
                self.status_message = action_result.message
                if action_result.save_tree:
                    self.tree.save()
                if action_result.refresh_tree:
                    self._refresh_tree()
        elif key == ord('m'):  # Move
            context = ActionContext(self, key, "move")
            action_result = self.operations_manager.handle("move", context)
            if action_result:
                self.status_message = action_result.message
                if action_result.save_tree:
                    self.tree.save()
                if action_result.refresh_tree:
                    self._refresh_tree()
                if action_result.clear_selection:
                    self.selection_manager.clear_selection()
        elif key == ord('?'):  # Help
            context = ActionContext(self, key, "help")
            action_result = self.tree_manager.handle("help", context)
            if action_result:
                self.status_message = action_result.message
            
    def _refresh_tree(self) -> None:
        """Refresh tree items."""
        self.tree_items = self.tree.get_tree_items(self.filtered_conversations, sort_by_date=self.sort_by_date)
        self.tree_view.set_items(self.tree_items)
        
        # Keep selection in bounds
        if self.tree_selected >= len(self.tree_items):
            self.tree_selected = max(0, len(self.tree_items) - 1)
            
        
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
        
            
    def _quick_filter(self) -> None:
        """Start filter mode (filters the tree)."""
        self.status_message = self.search_manager.start_filter_mode()
        self.current_view = ViewMode.SEARCH
        self.search_overlay.activate()
    
    def _start_vim_search(self) -> None:
        """Start vim-style search that jumps to matches."""
        self.status_message = self.search_manager.start_search_mode()
        self.current_view = ViewMode.SEARCH
        self.search_overlay.activate()
    
    


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="ChatGPT History Browser")
    parser.add_argument("conversations_file", nargs="?", help="Path to conversations file or Claude project")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--format", choices=["auto", "chatgpt", "claude"], default="auto",
                       help="Conversation format (auto-detected by default)")
    
    args = parser.parse_args()
    
    # Auto-detect Claude project if no file specified
    if not args.conversations_file:
        # Check if we're in a Claude project directory
        claude_project = find_claude_project_for_cwd()
        if claude_project:
            args.conversations_file = claude_project
            args.format = "claude"
        else:
            # Fall back to showing Claude project picker
            projects = list_claude_projects()
            if not projects:
                print("No Claude projects found and no conversation file specified.")
                print("Please provide a conversation file path or create a Claude project.")
                sys.exit(1)
            
            print("No conversation file specified. Available Claude projects:")
            print("=" * 50)
            for i, project in enumerate(projects, 1):
                name = project['name'].lstrip('-').replace('-', '/')
                count = project['conversation_count']
                print(f"{i:2}. {name} ({count} conversations)")
            
            print("\nUse: cgpt-tui ~/.claude/projects/<PROJECT_NAME>")
            sys.exit(0)
    
    if not Path(args.conversations_file).exists():
        print(f"File not found: {args.conversations_file}")
        sys.exit(1)
    
    try:
        tui = TUI(args.conversations_file, debug=args.debug, format=args.format)
        curses.wrapper(tui.run)
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()