#!/usr/bin/env python3
"""Simple conversation detail viewer."""

import curses
import textwrap
from typing import Optional
from src.core.models import Conversation, MessageRole


class DetailView:
    """Scrollable conversation viewer."""
    
    def __init__(self, stdscr):
        self.stdscr = stdscr
        # Use almost full screen, leaving room for status line
        h, w = stdscr.getmaxyx()
        self.y = 1
        self.x = 0
        self.width = w
        self.height = h - 2
        
        self.conversation: Optional[Conversation] = None
        self.scroll_offset = 0
        self.wrapped_lines = []
        
    def set_conversation(self, conversation: Conversation) -> None:
        """Set conversation to display."""
        self.conversation = conversation
        self.scroll_offset = 0
        self._wrap_messages()
        
    def _wrap_messages(self) -> None:
        """Wrap messages for display."""
        self.wrapped_lines = []
        if not self.conversation:
            return
            
        content_width = max(20, self.width - 4)
        
        for message in self.conversation.messages:
            # Add role header
            role_name = message.role.value.upper()
            self.wrapped_lines.append((role_name + ":", True))  # (text, is_header)
            
            # Wrap message content
            for paragraph in message.content.split('\n'):
                if paragraph.strip():
                    wrapped = textwrap.wrap(paragraph, width=content_width)
                    for line in wrapped:
                        self.wrapped_lines.append((line, False))
                else:
                    self.wrapped_lines.append(("", False))
                    
            # Add separator
            self.wrapped_lines.append(("", False))
            
    def handle_input(self, key: int) -> Optional[str]:
        """Handle keyboard input."""
        if key == curses.KEY_UP:
            self.scroll_offset = max(0, self.scroll_offset - 1)
        elif key == curses.KEY_DOWN:
            max_scroll = max(0, len(self.wrapped_lines) - self.height + 1)
            self.scroll_offset = min(max_scroll, self.scroll_offset + 1)
        elif key == curses.KEY_PPAGE:  # Page Up
            self.scroll_offset = max(0, self.scroll_offset - self.height + 2)
        elif key == curses.KEY_NPAGE:  # Page Down
            max_scroll = max(0, len(self.wrapped_lines) - self.height + 1)
            self.scroll_offset = min(max_scroll, self.scroll_offset + self.height - 2)
        elif key in (ord('q'), 27):  # q or ESC
            return "close_detail"
            
        return None
        
    def draw(self) -> None:
        """Draw the detail view."""
        # Clear area
        for row in range(self.height):
            self.stdscr.move(self.y + row, self.x)
            self.stdscr.clrtoeol()
            
        if not self.conversation:
            self.stdscr.addstr(
                self.y + self.height // 2, 
                self.x + 2, 
                "No conversation selected"
            )
            return
            
        # Title
        title = f"Conversation: {self.conversation.title}"
        if len(title) > self.width - 2:
            title = title[:self.width - 5] + "..."
        self.stdscr.addstr(self.y, self.x, title, curses.A_BOLD)
        
        # Messages
        visible_lines = self.height - 1
        for i in range(visible_lines):
            line_idx = self.scroll_offset + i
            if line_idx >= len(self.wrapped_lines):
                break
                
            text, is_header = self.wrapped_lines[line_idx]
            y_pos = self.y + 1 + i
            
            if is_header:
                # Role headers in color
                color = self._get_role_color(text)
                self.stdscr.addstr(y_pos, self.x + 2, text, color)
            else:
                # Message content indented
                if len(text) > self.width - 6:
                    text = text[:self.width - 9] + "..."
                self.stdscr.addstr(y_pos, self.x + 4, text)
                
    def _get_role_color(self, role_text: str) -> int:
        """Get color for role header."""
        if "USER:" in role_text:
            return curses.color_pair(3)
        elif "ASSISTANT:" in role_text:
            return curses.color_pair(4) if curses.has_colors() else 0
        else:
            return curses.A_BOLD