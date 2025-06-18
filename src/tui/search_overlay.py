#!/usr/bin/env python3
"""Simple search overlay for tree view."""

import curses
from typing import Optional


class SearchOverlay:
    """Simple search input overlay."""
    
    def __init__(self, stdscr, y: int, x: int, width: int):
        self.stdscr = stdscr
        self.y = y
        self.x = x
        self.width = width
        
        self.search_term = ""
        self.cursor_pos = 0
        self.active = False
        
    def activate(self) -> None:
        """Activate search mode."""
        self.active = True
        self.search_term = ""
        self.cursor_pos = 0
        
    def deactivate(self) -> None:
        """Deactivate search mode."""
        self.active = False
        
    def get_search_term(self) -> str:
        """Get current search term."""
        return self.search_term
    
    def _delete_previous_word(self) -> None:
        """Delete the word before the cursor (Ctrl+W behavior)."""
        if self.cursor_pos == 0:
            return
            
        # Find the start of the previous word
        # First, skip any whitespace before cursor
        pos = self.cursor_pos - 1
        while pos >= 0 and self.search_term[pos].isspace():
            pos -= 1
            
        # Then, skip the word characters
        while pos >= 0 and not self.search_term[pos].isspace():
            pos -= 1
            
        # pos is now at the character before the word (or -1)
        word_start = pos + 1
        
        # Delete from word_start to cursor_pos
        self.search_term = self.search_term[:word_start] + self.search_term[self.cursor_pos:]
        self.cursor_pos = word_start
        
    def handle_input(self, key: int) -> Optional[str]:
        """Handle keyboard input."""
        if not self.active:
            return None
            
        if key == 27:  # ESC
            return "search_cancelled"
        elif key == 7:  # Ctrl+G
            return "search_next_match"
        elif key == 23:  # Ctrl+W
            self._delete_previous_word()
            return "search_changed"
        elif key in (10, 13):  # Enter
            return "search_submitted"
        elif key in (curses.KEY_BACKSPACE, 127):
            if self.cursor_pos > 0:
                self.search_term = self.search_term[:self.cursor_pos-1] + self.search_term[self.cursor_pos:]
                self.cursor_pos -= 1
                return "search_changed"
        elif key == curses.KEY_LEFT:
            self.cursor_pos = max(0, self.cursor_pos - 1)
        elif key == curses.KEY_RIGHT:
            self.cursor_pos = min(len(self.search_term), self.cursor_pos + 1)
        elif key == curses.KEY_HOME:
            self.cursor_pos = 0
        elif key == curses.KEY_END:
            self.cursor_pos = len(self.search_term)
        elif 32 <= key <= 126:  # Printable characters
            if len(self.search_term) < 50:  # Max search length
                self.search_term = self.search_term[:self.cursor_pos] + chr(key) + self.search_term[self.cursor_pos:]
                self.cursor_pos += 1
                return "search_changed"
                
        return None
        
    def draw(self) -> None:
        """Draw search overlay."""
        if not self.active:
            return
            
        # Create search prompt
        prompt = "Search: "
        search_width = self.width - len(prompt) - 2
        
        # Truncate search term if too long
        display_term = self.search_term
        cursor_display_pos = self.cursor_pos
        
        if len(display_term) > search_width:
            # Scroll to keep cursor visible
            if self.cursor_pos > search_width - 3:
                start = self.cursor_pos - search_width + 3
                display_term = display_term[start:]
                cursor_display_pos = self.cursor_pos - start
            else:
                display_term = display_term[:search_width]
                
        # Draw search bar with border
        search_y = self.y
        try:
            # Clear line and draw border/background
            self.stdscr.addstr(search_y, self.x, "─" * self.width, curses.color_pair(2))
            
            # Draw prompt and search term
            full_text = prompt + display_term
            self.stdscr.addstr(search_y, self.x + 1, full_text, curses.color_pair(2) | curses.A_BOLD)
            
            # Position cursor
            cursor_x = self.x + 1 + len(prompt) + cursor_display_pos
            if cursor_x < self.x + self.width - 1:
                self.stdscr.move(search_y, cursor_x)
                
        except curses.error:
            pass