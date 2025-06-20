#!/usr/bin/env python3
"""Simple tree view with excellent UX."""

import curses
from datetime import datetime
from typing import List, Tuple, Optional
from src.tree.tree import TreeNode
from src.core.time_utils import format_relative_time


class TreeView:
    """Tree view with excellent visual hierarchy and interactions."""
    
    def __init__(self, stdscr):
        self.stdscr = stdscr
        # Use almost full screen, leaving room for status line
        h, w = stdscr.getmaxyx()
        self.y = 1
        self.x = 0
        self.width = w
        self.height = h - 2
        
        # Visual settings
        self.indent_size = 2
        self.guide_lines = True
        self.show_counts = True
        self.highlight_current_folder = True
        self.show_dates = True
        
        # State
        self.selected = 0
        self.offset = 0
        self.tree_items: List[Tuple[TreeNode, Optional[any], int]] = []
        self.selected_items: set = set()  # Multi-selected items
        self.last_key = None  # For vim-like double-key commands
        self.last_key_time = 0  # Timestamp for double-key timeout
        
    def set_items(self, items: List[Tuple[TreeNode, Optional[any], int]]) -> None:
        """Update tree items."""
        self.tree_items = items
        self.selected = min(self.selected, len(items) - 1) if items else 0
        
    def set_selected_items(self, selected_items: set) -> None:
        """Update multi-selected items."""
        self.selected_items = selected_items
        
    def handle_input(self, key: int) -> Optional[str]:
        """Handle keyboard input with vim-like bindings."""
        if not self.tree_items:
            return None
            
        import time
        current_time = time.time()
        
        # Handle double-key commands (gg, dd, yy, zz)
        if self.last_key and current_time - self.last_key_time < 0.5:
            if self.last_key == ord('g') and key == ord('g'):
                self.selected = 0
                self._ensure_visible()
                self.last_key = None
                return None
            elif self.last_key == ord('d') and key == ord('d'):
                self.last_key = None
                return "delete"
            elif self.last_key == ord('y') and key == ord('y'):
                self.last_key = None
                return "copy"
            elif self.last_key == ord('z') and key == ord('z'):
                self._center_on_selected()
                self.last_key = None
                return None
        
        # Store key for potential double-key commands
        if key in (ord('g'), ord('d'), ord('y'), ord('z')):
            self.last_key = key
            self.last_key_time = current_time
            return None
        else:
            self.last_key = None
            
        # Navigation
        if key in (curses.KEY_UP, ord('k')):
            self.move_up()
        elif key in (curses.KEY_DOWN, ord('j')):
            self.move_down()
        elif key == 4:  # Ctrl+D
            self.move_down(self.height // 2)
        elif key == 21:  # Ctrl+U  
            self.move_up(self.height // 2)
        elif key == 6:  # Ctrl+F - FZF fuzzy search
            return "fzf_search"
        elif key == 2:  # Ctrl+B
            self.move_up(self.height - 1)
        elif key == 16:  # Ctrl+P - Page up (alternative to Ctrl+B)
            self.move_up(self.height - 1)
        elif key == 14:  # Ctrl+N - Page down (alternative to Ctrl+F)
            self.move_down(self.height - 1)
        elif key == ord('H'):  # Jump to top of screen
            self.selected = self.offset
            self._ensure_visible()
        elif key == ord('M'):  # Jump to middle of screen
            self.selected = min(len(self.tree_items) - 1, self.offset + self.height // 2)
            self._ensure_visible()
        elif key == ord('L'):  # Jump to bottom of screen
            self.selected = min(len(self.tree_items) - 1, self.offset + self.height - 1)
            self._ensure_visible()
        elif key in (curses.KEY_HOME, ord('g')):
            self.selected = 0
        elif key in (curses.KEY_END, ord('G')):
            self.selected = len(self.tree_items) - 1
        elif key == ord('h'):  # Jump to parent
            return self._jump_to_parent()
        elif key == ord('l'):  # Expand or enter
            return self._expand_or_enter()
        elif key in (10, 13, curses.KEY_ENTER):
            return "view"
        elif key == ord('e'):
            return "edit"
        elif key == ord(' '):  # Toggle folder
            return "toggle"
        elif key == ord('*'):  # Expand all
            return "expand_all"
        elif key == ord('-'):  # Collapse all
            return "collapse_all"
        elif key == ord('K'):  # Move item up (Shift+K)
            return "move_up"
        elif key == ord('J'):  # Move item down (Shift+J)
            return "move_down"
        elif key == 566:  # Ctrl+Up
            return "move_up"
        elif key == 525:  # Ctrl+Down
            return "move_down"
        # Quick actions
        elif key == ord('x'):  # Quick delete
            return "delete"
        elif key == ord('u'):  # Undo
            return "undo"
        elif key == ord('.'):  # Repeat last action
            return "repeat"
        elif key == ord('p'):  # Paste/duplicate
            return "paste"
        # Function keys
        elif key == curses.KEY_F1:  # F1 - Help
            return "help"
        elif key == curses.KEY_F2:  # F2 - Rename
            return "rename"
        elif key == curses.KEY_F3:  # F3 - Search
            return "quick_filter"
        elif key == curses.KEY_F5:  # F5 - Refresh
            return "refresh"
        elif key == curses.KEY_DC:  # Delete key
            return "delete"
        elif key == curses.KEY_IC:  # Insert key
            return "new_folder"
        # Visual mode and selection
        elif key == ord('V'):  # Visual mode
            return "visual_mode"
        elif key == ord('>'):  # Indent
            return "indent"
        elif key == ord('<'):  # Outdent  
            return "outdent"
        # Quick filters
        elif key == ord('f'):  # Quick filter
            return "quick_filter"
        elif key == ord('F'):  # Show only folders
            return "filter_folders"
        elif key == ord('C'):  # Show only conversations
            return "filter_conversations"
        elif key == ord('a'):  # Show all
            return "show_all"
        # Numeric depth control
        elif ord('0') <= key <= ord('9'):
            depth = key - ord('0')
            return f"expand_depth_{depth}"
            
        return None
        
    def move_up(self, steps: int = 1) -> None:
        """Move selection up by specified steps."""
        self.selected = max(0, self.selected - steps)
        self._ensure_visible()
        
    def move_down(self, steps: int = 1) -> None:
        """Move selection down by specified steps."""
        self.selected = min(len(self.tree_items) - 1, self.selected + steps)
        self._ensure_visible()
        
    def _center_on_selected(self) -> None:
        """Center the view on the selected item."""
        if not self.tree_items:
            return
        # Calculate offset to center selected item
        target_offset = self.selected - self.height // 2
        max_offset = max(0, len(self.tree_items) - self.height + 1)
        self.offset = max(0, min(max_offset, target_offset))
        
    def _ensure_visible(self) -> None:
        """Ensure selected item is visible."""
        view_height = self.height - 1
        
        if self.selected < self.offset:
            self.offset = self.selected
        elif self.selected >= self.offset + view_height:
            self.offset = self.selected - view_height + 1
            
    def _jump_to_parent(self) -> Optional[str]:
        """Jump to parent folder."""
        if self.selected >= len(self.tree_items):
            return None
            
        node, _, depth = self.tree_items[self.selected]
        if depth == 0:
            return None
            
        # Find parent (previous item with depth - 1)
        for i in range(self.selected - 1, -1, -1):
            _, _, d = self.tree_items[i]
            if d == depth - 1:
                self.selected = i
                self._ensure_visible()
                break
                
        return None
        
    def _expand_or_enter(self) -> Optional[str]:
        """Expand folder or enter conversation."""
        if self.selected >= len(self.tree_items):
            return None
            
        node, conv, _ = self.tree_items[self.selected]
        if node.is_folder:
            return "toggle"
        else:
            return "select"
            
    def draw(self) -> None:
        """Draw the tree with enhanced visuals."""
        # Clear area
        for row in range(self.height):
            self.stdscr.move(self.y + row, self.x)
            self.stdscr.clrtoeol()
            
        if not self.tree_items:
            self.stdscr.addstr(self.y + self.height // 2, self.x + 2, "Empty tree")
            return
            
        # Count items for header
        folders = sum(1 for n, _, _ in self.tree_items if n.is_folder)
        convs = sum(1 for n, _, _ in self.tree_items if not n.is_folder)
        
        # Draw header with counts
        header = f"📁 {folders} folders, 💬 {convs} conversations"
        if convs > 0 and self.show_dates:
            # Add column headers for conversations
            header += " " * (max(0, 40 - len(header))) + "Modified    Created     Msgs"
        self.stdscr.addstr(self.y, self.x, header, curses.A_BOLD)
        
        # Draw tree items
        view_height = self.height - 1
        for i in range(view_height):
            idx = self.offset + i
            if idx >= len(self.tree_items):
                break
                
            self._draw_item(idx, self.y + 1 + i)
            
    def _draw_item(self, idx: int, y_pos: int) -> None:
        """Draw a single tree item with guide lines."""
        node, conv, depth = self.tree_items[idx]
        is_selected = idx == self.selected
        is_multi_selected = node.id in self.selected_items
        
        # Build indent with guide lines
        indent_chars = []
        for d in range(depth):
            # Check if we need a vertical line
            has_sibling = self._has_sibling_below(idx, d)
            if has_sibling and self.guide_lines:
                indent_chars.append("│ ")
            else:
                indent_chars.append("  ")
                
        indent = "".join(indent_chars)
        
        # Add branch character
        is_last = not self._has_sibling_below(idx, depth)
        if depth > 0 and self.guide_lines:
            branch = "└─" if is_last else "├─"
        else:
            branch = ""
            
        # Icon and name
        selection_marker = "✓ " if is_multi_selected else ""
        
        if node.is_folder:
            icon = "▼" if node.expanded else "▶"
            folder_icon = "📁"
            name = node.name
            
            # Add child count if enabled
            if self.show_counts:
                child_count = len(node.children)
                name = f"{name} ({child_count})"
                
            display = f"{indent}{branch}{selection_marker}{icon} {folder_icon} {name}"
            
            # Color
            if is_selected:
                attr = curses.color_pair(1)
            elif is_multi_selected:
                attr = curses.color_pair(3) | curses.A_REVERSE
            else:
                attr = curses.color_pair(3) | curses.A_BOLD
        else:
            icon = "💬"
            name = conv.title if conv else node.name
            
            # Format conversation info in claude --resume style
            if self.show_dates and conv:
                # Get times
                modified = format_relative_time(conv.update_time)
                created = format_relative_time(conv.create_time)
                msg_count = len(conv.messages) if conv.messages else 0
                
                # Calculate space needed for the format
                # icon (3) + space + [modified] (12) + space + [created] (12) + space + (msgs) (7) = ~37 chars
                format_overhead = 37
                max_name_len = self.width - len(indent) - len(branch) - len(selection_marker) - format_overhead - 2
                if len(name) > max_name_len and max_name_len > 0:
                    name = name[:max_name_len - 3] + "..."
                
                # Format: icon modified • created (msgs) title
                display = f"{indent}{branch}{selection_marker}{icon} {modified:<10} • {created:<10} ({msg_count:>4}) {name}"
            else:
                display = f"{indent}{branch}{selection_marker}{icon} {name}"
            
            # Color
            if is_selected:
                attr = curses.color_pair(1)
            elif is_multi_selected:
                attr = curses.A_REVERSE
            else:
                attr = 0
            
        # Truncate if needed
        max_width = self.width - 1
        if len(display) > max_width:
            display = display[:max_width - 3] + "..."
            
        # Draw with highlighting
        if is_selected:
            # Draw full width highlight
            self.stdscr.addstr(y_pos, self.x, " " * (self.width - 1), attr)
            
        self.stdscr.addstr(y_pos, self.x, display, attr)
        
    def _has_sibling_below(self, idx: int, depth: int) -> bool:
        """Check if there's a sibling at the given depth below this item."""
        for i in range(idx + 1, len(self.tree_items)):
            _, _, d = self.tree_items[i]
            if d < depth:
                return False
            if d == depth:
                return True
        return False
        
    def get_selected(self) -> Optional[Tuple[TreeNode, Optional[any], int]]:
        """Get currently selected item."""
        if 0 <= self.selected < len(self.tree_items):
            return self.tree_items[self.selected]
        return None