#!/usr/bin/env python3
"""
Base UI components for ChatGPT TUI.

Provides common functionality for view classes to reduce code duplication.
"""

# Standard library imports
import curses
import datetime
import textwrap
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple, Any

# Third-party imports
# (none currently)

# Local imports
from src.tree.tree_constants import UI_CONSTANTS


@dataclass
class ScrollState:
    """Manages scrolling state for views."""
    offset: int = 0
    selected: int = 0
    
    def reset(self) -> None:
        """Reset scroll state."""
        self.offset = 0
        self.selected = 0
    
    def move_up(self) -> None:
        """Move selection up."""
        if self.selected > 0:
            self.selected -= 1
    
    def move_down(self, max_items: int) -> None:
        """Move selection down."""
        if self.selected < max_items - 1:
            self.selected += 1
    
    def page_up(self, page_size: int) -> None:
        """Move selection up by page."""
        self.selected = max(0, self.selected - page_size)
    
    def page_down(self, max_items: int, page_size: int) -> None:
        """Move selection down by page."""
        self.selected = min(max_items - 1, self.selected + page_size)
    
    def adjust_offset(self, view_height: int) -> None:
        """Adjust scroll offset to keep selection visible."""
        if self.selected < self.offset:
            self.offset = self.selected
        elif self.selected >= self.offset + view_height:
            self.offset = self.selected - view_height + 1


class BaseView(ABC):
    """Base class for all TUI views."""
    
    def __init__(self, stdscr, start_y: int = 0, height: int = 0):
        self.stdscr = stdscr
        self.start_y = start_y
        
        # Handle curses attributes safely for testing
        try:
            self.height = height or (curses.LINES - start_y - UI_CONSTANTS['STATUS_BAR_HEIGHT'])
            self.width = curses.COLS
        except (AttributeError, TypeError):
            # Fallback for testing environments
            self.height = height or 24
            self.width = 80
            
        self.scroll_state = ScrollState()
    
    @abstractmethod
    def draw(self) -> None:
        """Draw the view content."""
        pass
    
    @abstractmethod  
    def handle_input(self, key: int) -> Optional[str]:
        """Handle input and return command if any."""
        pass
    
    def clear_area(self, start_row: int, num_rows: int) -> None:
        """Clear a specific area of the view."""
        for i in range(num_rows):
            try:
                self.stdscr.move(start_row + i, 0)
                self.stdscr.clrtoeol()
            except curses.error:
                break
    
    def draw_border(self, title: str = "") -> None:
        """Draw border around the view."""
        try:
            # Top border
            self.stdscr.hline(self.start_y, 0, curses.ACS_HLINE, self.width)
            if title:
                title_text = f" {title} "
                title_x = max(2, (self.width - len(title_text)) // 2)
                self.stdscr.addstr(self.start_y, title_x, title_text)
            
            # Bottom border  
            bottom_y = self.start_y + self.height - 1
            self.stdscr.hline(bottom_y, 0, curses.ACS_HLINE, self.width)
            
        except curses.error:
            pass
    
    def safe_addstr(self, y: int, x: int, text: str, 
                   attr: int = 0, max_width: Optional[int] = None) -> None:
        """Safely add string with bounds checking."""
        try:
            if max_width:
                text = text[:max_width]
            if y < curses.LINES and x < curses.COLS:
                # Ensure we don't write past the screen edge
                available_width = curses.COLS - x
                if len(text) > available_width:
                    text = text[:available_width]
                self.stdscr.addstr(y, x, text, attr)
        except curses.error:
            pass
    
    def draw_scroll_indicator(self, total_items: int, visible_height: int) -> None:
        """Draw scroll indicator on the right side."""
        if total_items <= visible_height:
            return
            
        try:
            indicator_height = max(1, (visible_height * visible_height) // total_items)
            indicator_start = (self.scroll_state.offset * visible_height) // total_items
            
            # Clear the right column first
            for i in range(visible_height):
                self.safe_addstr(self.start_y + 1 + i, self.width - 1, " ")
            
            # Draw the scroll indicator
            for i in range(indicator_height):
                indicator_y = self.start_y + 1 + indicator_start + i
                if indicator_y < self.start_y + 1 + visible_height:
                    self.safe_addstr(indicator_y, self.width - 1, "█")
                    
        except curses.error:
            pass


class NavigableListView(BaseView):
    """Base class for views with navigable lists."""
    
    def __init__(self, stdscr, start_y: int = 0, height: int = 0):
        super().__init__(stdscr, start_y, height)
        self.items: List[Any] = []
    
    @abstractmethod
    def format_item(self, item: Any, index: int, is_selected: bool) -> str:
        """Format an item for display."""
        pass
    
    def get_visible_range(self) -> Tuple[int, int]:
        """Get the range of items that should be visible."""
        visible_height = self.height - UI_CONSTANTS['HEADER_HEIGHT'] - UI_CONSTANTS['BORDER_HEIGHT']
        self.scroll_state.adjust_offset(visible_height)
        
        start_idx = self.scroll_state.offset
        end_idx = min(len(self.items), start_idx + visible_height)
        return start_idx, end_idx
    
    def draw_items(self, title: str = "") -> None:
        """Draw the list of items."""
        self.clear_area(self.start_y, self.height)
        
        if title:
            self.draw_border(title)
        
        if not self.items:
            self.safe_addstr(
                self.start_y + 2, 2, 
                "No items to display",
                curses.A_DIM
            )
            return
        
        start_idx, end_idx = self.get_visible_range()
        display_y = self.start_y + UI_CONSTANTS['HEADER_HEIGHT']
        
        for i in range(start_idx, end_idx):
            is_selected = (i == self.scroll_state.selected)
            item_text = self.format_item(self.items[i], i, is_selected)
            
            # Highlight selected item
            attr = curses.A_REVERSE if is_selected else 0
            
            self.safe_addstr(
                display_y, 2, item_text, 
                attr, self.width - 4
            )
            display_y += 1
        
        # Draw scroll indicator
        visible_height = self.height - UI_CONSTANTS['HEADER_HEIGHT'] - UI_CONSTANTS['BORDER_HEIGHT']
        self.draw_scroll_indicator(len(self.items), visible_height)
    
    def handle_navigation_input(self, key: int) -> Optional[str]:
        """Handle common navigation input."""
        if not self.items:
            return None
            
        if key == curses.KEY_UP or key == ord('k'):
            self.scroll_state.move_up()
            return "refresh"
            
        elif key == curses.KEY_DOWN or key == ord('j'):
            self.scroll_state.move_down(len(self.items))
            return "refresh"
            
        elif key == curses.KEY_PPAGE:
            page_size = self.height - UI_CONSTANTS['HEADER_HEIGHT'] - UI_CONSTANTS['BORDER_HEIGHT']
            self.scroll_state.page_up(page_size)
            return "refresh"
            
        elif key == curses.KEY_NPAGE:
            page_size = self.height - UI_CONSTANTS['HEADER_HEIGHT'] - UI_CONSTANTS['BORDER_HEIGHT']
            self.scroll_state.page_down(len(self.items), page_size)
            return "refresh"
            
        elif key == curses.KEY_HOME:
            self.scroll_state.selected = 0
            return "refresh"
            
        elif key == curses.KEY_END:
            self.scroll_state.selected = len(self.items) - 1
            return "refresh"
            
        return None
    
    def get_selected_item(self) -> Optional[Any]:
        """Get the currently selected item."""
        if not self.items or self.scroll_state.selected >= len(self.items):
            return None
        return self.items[self.scroll_state.selected]


class InputHandler:
    """Handles common input patterns across views."""
    
    @staticmethod
    def is_quit_key(key: int) -> bool:
        """Check if key is a quit command."""
        return key == ord('q') or key == 27  # 'q' or ESC
    
    @staticmethod
    def is_help_key(key: int) -> bool:
        """Check if key is a help command."""
        return key == ord('?') or key == curses.KEY_F1
    
    @staticmethod
    def is_search_key(key: int) -> bool:
        """Check if key is a search command."""
        return key == ord('/') or key == ord('s')
    
    @staticmethod
    def is_enter_key(key: int) -> bool:
        """Check if key is enter/select."""
        return key == ord('\n') or key == ord('\r') or key == curses.KEY_ENTER


class UIFormatter:
    """Utilities for formatting text in the UI."""
    
    @staticmethod
    def truncate_text(text: str, max_width: int, suffix: str = "...") -> str:
        """Truncate text to fit within max_width."""
        if len(text) <= max_width:
            return text
        return text[:max_width - len(suffix)] + suffix
    
    @staticmethod
    def wrap_text(text: str, width: int, indent: int = 0) -> List[str]:
        """Wrap text to specified width with optional indentation."""
        wrapper = textwrap.TextWrapper(
            width=width,
            initial_indent=" " * indent,
            subsequent_indent=" " * indent,
            break_long_words=True,
            break_on_hyphens=True
        )
        return wrapper.wrap(text)
    
    @staticmethod
    def format_timestamp(timestamp: float) -> str:
        """Format timestamp for display."""
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    
    @staticmethod
    def format_size(size: int) -> str:
        """Format file size for display."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"