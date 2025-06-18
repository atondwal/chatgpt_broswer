#!/usr/bin/env python3
"""Terminal UI for browsing ChatGPT conversations."""

import argparse
import curses
import logging
import sys
from enum import Enum
from pathlib import Path

from src.core.simple_loader import load_conversations
from src.tree.simple_tree import ConversationTree
from src.tui.simple_detail import DetailView
from src.tui.simple_input import get_input, confirm, select_folder
from src.tui.enhanced_tree_ux import EnhancedTreeView
from src.tui.simple_search_overlay import SearchOverlay


class ViewMode(Enum):
    """Available view modes."""
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
        
        # Multi-select state
        self.selected_items = set()  # Set of node IDs that are selected
        self.multi_select_mode = False  # Whether we're in multi-select mode
        
        
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
        self.tree_view = EnhancedTreeView(stdscr, 1, 0, width, height - 2)
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
            help_text = {
                ViewMode.TREE: f"↑/↓:Navigate Enter:Open Space:Select Ctrl+A:All /:Search Shift+J/K:Move{multi_info} ?:Help q:Quit",
                ViewMode.SEARCH: "Type:Search ESC:Cancel Enter:Apply",
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
                if self.search_term:
                    self.status_message = f"Search: '{self.search_term}' ({len(self.filtered_conversations)} matches)"
            elif result == "search_changed":
                self._update_search(self.search_overlay.get_search_term())
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
            self.current_view = ViewMode.SEARCH
            self.search_overlay.activate()
        elif key == 1:  # Ctrl+A
            self._select_all()
        elif key == ord(' '):  # Space for multi-select
            self._toggle_item_selection()
            
        # Tree navigation (only view mode now)
        if self.current_view == ViewMode.TREE:
            self._handle_tree_key(key)
            
    def _handle_tree_key(self, key: int) -> None:
        """Handle keys in tree view."""
        result = self.tree_view.handle_input(key)
        
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
                        self.tree.save()
                        self._refresh_tree()
                        self._move_cursor_to_item(node.id)
                        self.status_message = f"Moved '{node.name}' down"
                    else:
                        self.status_message = "Cannot move down"
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
                    
            self.tree.create_folder(name, parent_id)
            self.tree.save()
            self._refresh_tree()
            self.status_message = f"Created '{name}'"
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
            "Tree View Controls:",
            "",
            "Navigation:",
            "  ↑/k     - Move up",
            "  ↓/j     - Move down",
            "  g       - Go to top",
            "  G       - Go to bottom",
            "  h       - Jump to parent folder",
            "  l       - Expand folder / Enter conversation",
            "",
            "Actions:",
            "  Enter   - Open conversation / Toggle folder",
            "  Space   - Select/deselect item (multi-select)",
            "  Ctrl+A  - Select all items",
            "  ESC     - Clear selection (or quit if none)",
            "  *       - Expand all folders",
            "  -       - Collapse all folders",
            "",
            "Reordering:",
            "  Shift+J - Move item(s) down",
            "  Shift+K - Move item(s) up",
            "",
            "Organization:",
            "  n       - Create new folder",
            "  r       - Rename item",
            "  d       - Delete item",
            "  m       - Move item(s) to folder",
            "  o       - Toggle sort (date/name)",
            "",
            "Other:",
            "  /       - Search conversations",
            "  q       - Quit",
            "",
            "Multi-select: Use Space to select multiple items,",
            "then use Shift+J/K to reorder or 'm' to move all.",
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
        self._refresh_tree()
        self.status_message = f"Sorting by {'date (newest first)' if self.sort_by_date else 'name (A-Z)'}"
        
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