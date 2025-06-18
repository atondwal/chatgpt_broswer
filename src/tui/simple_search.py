#!/usr/bin/env python3
"""Simple search input for TUI."""

import curses
from typing import Optional, Callable


class SearchView:
    """Search input overlay."""
    
    def __init__(self, stdscr, y: int, x: int, width: int, height: int = 1):
        self.stdscr = stdscr
        self.y = y
        self.x = x
        self.width = width
        self.height = height
        
        self.search_term = ""
        self.cursor_pos = 0
        self.is_active = False
        self.on_change: Optional[Callable[[str], None]] = None
        
    def set_search_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for when search term changes."""
        self.on_change = callback
        
    def activate(self) -> None:
        """Start search mode."""
        self.is_active = True
        self.search_term = ""
        self.cursor_pos = 0
        if self.on_change:
            self.on_change("")
            
    def deactivate(self) -> None:
        """Exit search mode."""
        self.is_active = False
        
    def get_search_term(self) -> str:
        """Get current search term."""
        return self.search_term
        
    def handle_input(self, key: int) -> Optional[str]:
        """Handle keyboard input."""
        if not self.is_active:
            return None
            
        # Special keys
        if key == 27:  # ESC
            self.deactivate()
            return "search_cancelled"
        elif key in (10, 13):  # Enter
            return "search_submitted"
        elif key in (curses.KEY_BACKSPACE, 127, 8):  # Backspace
            if self.cursor_pos > 0:
                self.search_term = (
                    self.search_term[:self.cursor_pos-1] + 
                    self.search_term[self.cursor_pos:]
                )
                self.cursor_pos -= 1
                if self.on_change:
                    self.on_change(self.search_term)
        elif key == curses.KEY_LEFT:
            self.cursor_pos = max(0, self.cursor_pos - 1)
        elif key == curses.KEY_RIGHT:
            self.cursor_pos = min(len(self.search_term), self.cursor_pos + 1)
        elif 32 <= key <= 126:  # Printable characters
            self.search_term = (
                self.search_term[:self.cursor_pos] + 
                chr(key) + 
                self.search_term[self.cursor_pos:]
            )
            self.cursor_pos += 1
            if self.on_change:
                self.on_change(self.search_term)
                
        return None
        
    def draw(self) -> None:
        """Draw search overlay."""
        if not self.is_active:
            return
            
        # Clear the search line
        self.stdscr.move(self.y, self.x)
        self.stdscr.clrtoeol()
        
        # Draw prompt and search term
        prompt = "Search: "
        self.stdscr.addstr(self.y, self.x, prompt)
        
        # Draw search term with cursor
        term_x = self.x + len(prompt)
        max_term_width = self.width - len(prompt) - 1
        
        # Handle long search terms with scrolling
        if len(self.search_term) > max_term_width:
            # Scroll to keep cursor visible
            start = max(0, self.cursor_pos - max_term_width + 5)
            visible_term = self.search_term[start:start + max_term_width]
            cursor_offset = self.cursor_pos - start
        else:
            visible_term = self.search_term
            cursor_offset = self.cursor_pos
            
        # Draw the visible part
        self.stdscr.addstr(self.y, term_x, visible_term)
        
        # Position cursor
        self.stdscr.move(self.y, term_x + cursor_offset)