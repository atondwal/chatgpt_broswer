#!/usr/bin/env python3
"""
Search view component for the ChatGPT TUI.

Provides real-time search functionality with cursor support and filtering.
"""

import curses
from dataclasses import dataclass
from typing import List, Optional, Callable

from .ui_base import BaseView


@dataclass
class SearchState:
    """Manages search interface state."""
    term: str = ""
    cursor_pos: int = 0
    is_active: bool = False
    
    def clear(self) -> None:
        """Clear the search state."""
        self.term = ""
        self.cursor_pos = 0
    
    def set_term(self, term: str) -> None:
        """Set the search term and position cursor at end."""
        self.term = term
        self.cursor_pos = len(term)


class SearchView(BaseView):
    """Modern search interface with real-time filtering."""
    
    def __init__(self, stdscr, y: int, x: int, width: int, height: int = 1):
        """
        Initialize search view.
        
        Args:
            stdscr: Curses screen object
            y: Starting Y position  
            x: Starting X position
            width: Width of search area
            height: Height of search area (typically 1)
        """
        super().__init__(stdscr, y, x, width, height)
        self.state = SearchState()
        self.on_search_changed: Optional[Callable[[str], None]] = None
        self.prompt = "Search: "
        
    def activate(self) -> None:
        """Activate search mode."""
        self.state.is_active = True
        self.state.clear()
        if self.on_search_changed:
            self.on_search_changed(self.state.term)
        
    def deactivate(self) -> None:
        """Deactivate search mode."""
        self.state.is_active = False
        self.state.clear()
        if self.on_search_changed:
            self.on_search_changed("")
    
    def handle_input(self, key: int) -> Optional[str]:
        """
        Handle search input.
        
        Args:
            key: Input key code
            
        Returns:
            Command string or None
        """
        if not self.state.is_active:
            return None
            
        term_changed = False
        
        # Handle special keys
        if key == 27:  # ESC
            self.deactivate()
            return "search_cancelled"
        elif key == 10 or key == 13:  # Enter
            return "search_submitted"
        elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
            if self.state.cursor_pos > 0:
                self.state.term = (
                    self.state.term[:self.state.cursor_pos - 1] + 
                    self.state.term[self.state.cursor_pos:]
                )
                self.state.cursor_pos -= 1
                term_changed = True
        elif key == curses.KEY_LEFT:
            self.state.cursor_pos = max(0, self.state.cursor_pos - 1)
        elif key == curses.KEY_RIGHT:
            self.state.cursor_pos = min(len(self.state.term), self.state.cursor_pos + 1)
        elif key == curses.KEY_HOME:
            self.state.cursor_pos = 0
        elif key == curses.KEY_END:
            self.state.cursor_pos = len(self.state.term)
        elif key == curses.KEY_DC:  # Delete key
            if self.state.cursor_pos < len(self.state.term):
                self.state.term = (
                    self.state.term[:self.state.cursor_pos] + 
                    self.state.term[self.state.cursor_pos + 1:]
                )
                term_changed = True
        elif 32 <= key <= 126:  # Printable ASCII
            char = chr(key)
            self.state.term = (
                self.state.term[:self.state.cursor_pos] + 
                char + 
                self.state.term[self.state.cursor_pos:]
            )
            self.state.cursor_pos += 1
            term_changed = True
        
        # Notify of search term changes
        if term_changed and self.on_search_changed:
            self.on_search_changed(self.state.term)
            
        return None
    
    def draw(self) -> None:
        """Draw the search interface."""
        try:
            if not self.state.is_active:
                return
                
            # Clear the area
            self.clear_area()
            
            # Draw search prompt
            self.stdscr.attron(curses.color_pair(2))  # Header color
            self.stdscr.addstr(self.y, self.x, self.prompt)
            self.stdscr.attroff(curses.color_pair(2))
            
            # Calculate available space for search term
            search_x = self.x + len(self.prompt)
            max_width = self.width - len(self.prompt) - 1
            
            if max_width <= 0:
                return
                
            # Handle horizontal scrolling for long search terms
            display_term = self.state.term
            display_cursor = self.state.cursor_pos
            
            if len(display_term) > max_width:
                if self.state.cursor_pos > max_width - 1:
                    # Scroll to keep cursor visible
                    start_offset = self.state.cursor_pos - max_width + 1
                    display_term = display_term[start_offset:]
                    display_cursor = max_width - 1
                else:
                    # Truncate from the right
                    display_term = display_term[:max_width]
            
            # Draw search term
            self.stdscr.addstr(self.y, search_x, display_term)
            
            # Position cursor
            cursor_x = search_x + display_cursor
            if cursor_x < self.x + self.width:
                self.stdscr.move(self.y, cursor_x)
                
        except curses.error:
            pass
    
    def clear_area(self) -> None:
        """Clear the search area."""
        try:
            for row in range(self.height):
                self.stdscr.move(self.y + row, self.x)
                self.stdscr.clrtoeol()
        except curses.error:
            pass
    
    def get_search_term(self) -> str:
        """Get the current search term."""
        return self.state.term
    
    def is_active(self) -> bool:
        """Check if search is currently active."""
        return self.state.is_active
    
    def set_search_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback function for search term changes."""
        self.on_search_changed = callback