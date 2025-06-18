#!/usr/bin/env python3
"""Enhanced tree view with excellent UX."""

import curses
from typing import List, Tuple, Optional
from src.tree.simple_tree import TreeNode


class EnhancedTreeView:
    """Tree view with improved visual hierarchy and interactions."""
    
    def __init__(self, stdscr, y: int, x: int, width: int, height: int):
        self.stdscr = stdscr
        self.y = y
        self.x = x
        self.width = width
        self.height = height
        
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
        
    def set_items(self, items: List[Tuple[TreeNode, Optional[any], int]]) -> None:
        """Update tree items."""
        self.tree_items = items
        self.selected = min(self.selected, len(items) - 1) if items else 0
        
    def handle_input(self, key: int) -> Optional[str]:
        """Handle keyboard input with vim-like bindings."""
        if not self.tree_items:
            return None
            
        # Navigation
        if key in (curses.KEY_UP, ord('k')):
            self.move_up()
        elif key in (curses.KEY_DOWN, ord('j')):
            self.move_down()
        elif key in (curses.KEY_HOME, ord('g')):
            self.selected = 0
        elif key in (curses.KEY_END, ord('G')):
            self.selected = len(self.tree_items) - 1
        elif key == ord('h'):  # Jump to parent
            return self._jump_to_parent()
        elif key == ord('l'):  # Expand or enter
            return self._expand_or_enter()
        elif key in (10, 13, curses.KEY_ENTER):
            return "select"
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
            
        return None
        
    def move_up(self) -> None:
        """Move selection up."""
        self.selected = max(0, self.selected - 1)
        self._ensure_visible()
        
    def move_down(self) -> None:
        """Move selection down."""
        self.selected = min(len(self.tree_items) - 1, self.selected + 1)
        self._ensure_visible()
        
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
        if node.is_folder:
            icon = "▼" if node.expanded else "▶"
            folder_icon = "📁"
            name = node.name
            
            # Add child count if enabled
            if self.show_counts:
                child_count = len(node.children)
                name = f"{name} ({child_count})"
                
            display = f"{indent}{branch}{icon} {folder_icon} {name}"
            
            # Color
            if is_selected:
                attr = curses.color_pair(1)
            else:
                attr = curses.color_pair(3) | curses.A_BOLD
        else:
            icon = "💬"
            name = conv.title if conv else node.name
            
            # Add date for conversations if enabled
            if self.show_dates and conv and conv.create_time:
                from datetime import datetime
                date_str = datetime.fromtimestamp(conv.create_time).strftime("%Y-%m-%d")
                # Calculate space for date
                base_display = f"{indent}{branch}{icon} {name}"
                max_name_width = self.width - len(indent) - len(branch) - 4 - 12  # Reserve 12 chars for date
                if len(name) > max_name_width:
                    name = name[:max_name_width - 3] + "..."
                display = f"{indent}{branch}{icon} {name}"
                # Right-align date
                padding = self.width - len(display) - 12
                if padding > 0:
                    display += " " * padding + f"[{date_str}]"
            else:
                display = f"{indent}{branch}{icon} {name}"
            
            # Color - dim the date
            attr = curses.color_pair(1) if is_selected else 0
            
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