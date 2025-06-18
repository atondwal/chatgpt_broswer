#!/usr/bin/env python3
"""
Conversation detail view component for the ChatGPT TUI.

Provides scrollable message viewing with proper text wrapping and formatting.
"""

import curses
import textwrap
from typing import List, Optional, Tuple

from src.core.models import Conversation, MessageRole
from .ui_base import BaseView, ScrollState


class ConversationDetailView(BaseView):
    """Scrollable conversation detail view with message formatting."""
    
    def __init__(self, stdscr, y: int, x: int, width: int, height: int):
        """
        Initialize conversation detail view.
        
        Args:
            stdscr: Curses screen object
            y: Starting Y position
            x: Starting X position
            width: Width of detail area
            height: Height of detail area
        """
        super().__init__(stdscr, y, x, width, height)
        self.conversation: Optional[Conversation] = None
        self.scroll_state = ScrollState()
        self.formatted_messages: List[Tuple[MessageRole, List[str]]] = []
        self.total_lines = 0
        
    def set_conversation(self, conversation: Conversation) -> None:
        """Set the conversation to display."""
        self.conversation = conversation
        self.scroll_state.offset = 0
        self._format_messages()
    
    def clear_conversation(self) -> None:
        """Clear the current conversation."""
        self.conversation = None
        self.formatted_messages = []
        self.total_lines = 0
        self.scroll_state.offset = 0
    
    def handle_input(self, key: int) -> Optional[str]:
        """
        Handle scrolling input.
        
        Args:
            key: Input key code
            
        Returns:
            Command string or None
        """
        if key == curses.KEY_UP or key == ord('k'):
            self.scroll_up()
        elif key == curses.KEY_DOWN or key == ord('j'):
            self.scroll_down()
        elif key == curses.KEY_PPAGE:  # Page Up
            self.page_up()
        elif key == curses.KEY_NPAGE:  # Page Down
            self.page_down()
        elif key == curses.KEY_HOME:
            self.scroll_to_top()
        elif key == curses.KEY_END:
            self.scroll_to_bottom()
        elif key == ord('q') or key == 27:  # ESC
            return "close_detail"
        
        return None
    
    def scroll_up(self) -> None:
        """Scroll up one line."""
        if self.scroll_state.offset > 0:
            self.scroll_state.offset -= 1
    
    def scroll_down(self) -> None:
        """Scroll down one line."""
        visible_lines = self.height - 1  # Reserve one line for header
        max_scroll = max(0, self.total_lines - visible_lines)
        if self.scroll_state.offset < max_scroll:
            self.scroll_state.offset += 1
    
    def page_up(self) -> None:
        """Page up in the message view."""
        page_size = max(1, self.height - 2)
        self.scroll_state.offset = max(0, self.scroll_state.offset - page_size)
    
    def page_down(self) -> None:
        """Page down in the message view."""
        page_size = max(1, self.height - 2)
        visible_lines = self.height - 1
        max_scroll = max(0, self.total_lines - visible_lines)
        self.scroll_state.offset = min(max_scroll, self.scroll_state.offset + page_size)
    
    def scroll_to_top(self) -> None:
        """Scroll to the top of the conversation."""
        self.scroll_state.offset = 0
    
    def scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the conversation."""
        visible_lines = self.height - 1
        max_scroll = max(0, self.total_lines - visible_lines)
        self.scroll_state.offset = max_scroll
    
    def _format_messages(self) -> None:
        """Format messages for display with text wrapping."""
        if not self.conversation:
            self.formatted_messages = []
            self.total_lines = 0
            return
        
        self.formatted_messages = []
        content_width = max(20, self.width - 4)  # Leave margins, minimum width
        total_lines = 0
        
        for message in self.conversation.messages:
            # Format role header
            role_display = self._format_role(message.role)
            
            # Wrap message content
            wrapped_lines = []
            if message.content.strip():
                for line in message.content.split('\n'):
                    if line.strip():
                        wrapped_lines.extend(textwrap.wrap(
                            line, 
                            width=content_width,
                            break_long_words=True,
                            break_on_hyphens=True
                        ))
                    else:
                        wrapped_lines.append("")
            else:
                wrapped_lines = ["[Empty message]"]
            
            self.formatted_messages.append((message.role, wrapped_lines))
            
            # Count total lines (role header + content + separator)
            total_lines += 1 + len(wrapped_lines) + 1  # +1 for role, +1 for blank line
        
        self.total_lines = total_lines
    
    def _format_role(self, role: MessageRole) -> str:
        """Format a message role for display."""
        role_names = {
            MessageRole.USER: "USER",
            MessageRole.ASSISTANT: "ASSISTANT", 
            MessageRole.SYSTEM: "SYSTEM",
            MessageRole.TOOL: "TOOL",
            MessageRole.THOUGHTS: "THOUGHTS",
            MessageRole.REASONING_RECAP: "REASONING",
            MessageRole.USER_EDITABLE_CONTEXT: "CONTEXT",
        }
        return role_names.get(role, role.value.upper())
    
    def _get_role_color(self, role: MessageRole) -> int:
        """Get color pair for a message role."""
        role_colors = {
            MessageRole.USER: 3,      # User color
            MessageRole.ASSISTANT: 4, # Assistant color
            MessageRole.SYSTEM: 5,    # System color
            MessageRole.TOOL: 6,      # Tool color
        }
        return role_colors.get(role, 1)  # Default color
    
    def draw(self) -> None:
        """Draw the conversation detail view."""
        try:
            # Clear the area
            self.clear_area()
            
            if not self.conversation:
                self.stdscr.addstr(
                    self.y + self.height // 2, 
                    self.x + 2, 
                    "No conversation selected"
                )
                return
            
            # Draw header
            header = f"Conversation: {self.conversation.title}"
            if len(header) > self.width - 2:
                header = header[:self.width - 5] + "..."
            
            self.stdscr.attron(curses.color_pair(2))  # Header color
            self.stdscr.addstr(self.y, self.x, header)
            self.stdscr.attroff(curses.color_pair(2))
            
            # Draw messages
            current_line = 0
            y_pos = self.y + 1
            visible_lines = self.height - 1
            
            for role, lines in self.formatted_messages:
                # Check if we've scrolled past this message entirely
                message_total_lines = 1 + len(lines) + 1  # role + content + blank
                if current_line + message_total_lines <= self.scroll_state.offset:
                    current_line += message_total_lines
                    continue
                
                # Check if we're past the visible area
                if y_pos >= self.y + self.height:
                    break
                
                # Draw role header (if visible)
                if current_line >= self.scroll_state.offset:
                    if y_pos < self.y + self.height:
                        role_text = f"{self._format_role(role)}:"
                        color = self._get_role_color(role)
                        self.stdscr.attron(curses.color_pair(color))
                        self.stdscr.addstr(y_pos, self.x + 2, role_text)
                        self.stdscr.attroff(curses.color_pair(color))
                        y_pos += 1
                current_line += 1
                
                # Draw message content lines
                for line in lines:
                    if current_line >= self.scroll_state.offset and y_pos < self.y + self.height:
                        # Truncate line if too long
                        display_line = line
                        if len(display_line) > self.width - 4:
                            display_line = display_line[:self.width - 7] + "..."
                        
                        self.stdscr.addstr(y_pos, self.x + 4, display_line)
                        y_pos += 1
                    current_line += 1
                
                # Add blank line between messages
                if current_line >= self.scroll_state.offset and y_pos < self.y + self.height:
                    y_pos += 1
                current_line += 1
                
        except curses.error:
            pass
    
    def get_scroll_info(self) -> Tuple[int, int, int]:
        """
        Get scroll information for status display.
        
        Returns:
            Tuple of (current_offset, total_lines, visible_lines)
        """
        visible_lines = self.height - 1
        return (self.scroll_state.offset, self.total_lines, visible_lines)