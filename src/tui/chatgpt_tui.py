#!/usr/bin/env python3
"""
ChatGPT History Browser - Terminal User Interface

Professional curses-based interface for browsing ChatGPT conversation history.
Provides navigation, search, and viewing capabilities with a clean, modern TUI.

Author: Generated with Claude Code
"""

# Standard library imports
import argparse
import curses
import logging
import sys
import textwrap
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

# Third-party imports
# (none currently)

# Local imports
from src.core.chatgpt_browser import (
    Conversation, ConversationLoader, ConversationSearcher, 
    ConversationExporter, MessageRole
)
from src.tree.conversation_tree import (
    ConversationOrganizer, TreeNode, NodeType, ConversationMetadata
)
from src.tree.tree_constants import TREE_CHARS, UI_CONSTANTS, COLOR_PAIRS, SHORTCUTS
from src.tui.ui_base import (
    BaseView, NavigableListView, ScrollState, InputHandler, UIFormatter
)


class ViewMode(Enum):
    """Available view modes in the TUI."""
    CONVERSATION_LIST = "list"
    CONVERSATION_TREE = "tree"
    CONVERSATION_DETAIL = "detail"
    SEARCH = "search"
    HELP = "help"


class ColorPair(Enum):
    """Color pairs for the TUI."""
    DEFAULT = COLOR_PAIRS["DEFAULT"]
    HEADER = COLOR_PAIRS["HEADER"]
    SELECTED = COLOR_PAIRS["SELECTED"]
    BORDER = COLOR_PAIRS["BORDER"]
    STATUS = COLOR_PAIRS["STATUS"]
    USER_MESSAGE = COLOR_PAIRS["USER_MESSAGE"]
    ASSISTANT_MESSAGE = COLOR_PAIRS["ASSISTANT_MESSAGE"]
    SYSTEM_MESSAGE = COLOR_PAIRS["SYSTEM_MESSAGE"]
    SEARCH_HIGHLIGHT = COLOR_PAIRS["SEARCH_HIGHLIGHT"]
    ERROR = COLOR_PAIRS["ERROR"]
    FOLDER = COLOR_PAIRS["FOLDER"]
    CONVERSATION_TREE = COLOR_PAIRS["CONVERSATION_TREE"]


@dataclass
class WindowDimensions:
    """Represents window dimensions and positions."""
    height: int
    width: int
    start_y: int = 0
    start_x: int = 0

    @property
    def max_y(self) -> int:
        return self.start_y + self.height - 1

    @property
    def max_x(self) -> int:
        return self.start_x + self.width - 1


class StatusBar:
    """Manages the status bar at the bottom of the screen."""
    
    def __init__(self, stdscr, y: int, width: int):
        self.stdscr = stdscr
        self.y = y
        self.width = width
        self.message = ""
        self.error = False

    def show_message(self, message: str, is_error: bool = False) -> None:
        """Display a message in the status bar."""
        self.message = message[:self.width - 2]
        self.error = is_error
        self.refresh()

    def show_shortcuts(self, shortcuts: Dict[str, str]) -> None:
        """Display keyboard shortcuts in the status bar."""
        shortcut_text = " | ".join([f"{key}: {desc}" for key, desc in shortcuts.items()])
        self.message = shortcut_text[:self.width - 2]
        self.error = False
        self.refresh()

    def refresh(self) -> None:
        """Refresh the status bar display."""
        try:
            self.stdscr.move(self.y, 0)
            self.stdscr.clrtoeol()
            
            color = ColorPair.ERROR.value if self.error else ColorPair.STATUS.value
            self.stdscr.attron(curses.color_pair(color))
            self.stdscr.addstr(self.y, 0, self.message[:self.width])
            self.stdscr.attroff(curses.color_pair(color))
        except curses.error:
            pass  # Ignore drawing errors at screen boundaries


class ConversationListView(NavigableListView):
    """Manages the conversation list view using base UI components."""
    
    def __init__(self, stdscr, dimensions: WindowDimensions):
        super().__init__(stdscr, dimensions.start_y, dimensions.height)
        self.dims = dimensions
        self.conversations: List[Conversation] = []
        self.filtered_conversations: List[Tuple[int, Conversation]] = []
        self.search_term = ""
        
    def set_conversations(self, conversations: List[Conversation]) -> None:
        """Set the conversations to display."""
        self.conversations = conversations
        self.filtered_conversations = [(i, conv) for i, conv in enumerate(conversations)]
        self.items = [conv for _, conv in self.filtered_conversations]
        self.scroll_state.reset()

    def filter_conversations(self, search_term: str) -> None:
        """Filter conversations based on search term."""
        self.search_term = search_term.lower()
        if not self.search_term:
            self.filtered_conversations = [(i, conv) for i, conv in enumerate(self.conversations)]
        else:
            self.filtered_conversations = [
                (i, conv) for i, conv in enumerate(self.conversations)
                if self.search_term in conv.title.lower()
            ]
        self.items = [conv for _, conv in self.filtered_conversations]
        self.scroll_state.reset()

    def get_selected_conversation(self) -> Optional[Conversation]:
        """Get the currently selected conversation."""
        return self.get_selected_item()

    def format_item(self, item: Conversation, index: int, is_selected: bool) -> str:
        """Format a conversation for display."""
        return UIFormatter.truncate_text(item.title, self.width - 6)

    def handle_input(self, key: int) -> Optional[str]:
        """Handle input for conversation list."""
        # First try navigation
        nav_result = self.handle_navigation_input(key)
        if nav_result:
            return nav_result
            
        # Handle list-specific input
        if InputHandler.is_enter_key(key):
            return "select_conversation"
        elif key == ord('/') or key == ord('s'):
            return "start_search"
        elif InputHandler.is_quit_key(key):
            return "quit"
        elif InputHandler.is_help_key(key):
            return "show_help"
            
        return None

    # Legacy compatibility methods
    @property 
    def current_index(self) -> int:
        """Get current selection index for compatibility."""
        return self.scroll_state.selected
    
    @current_index.setter
    def current_index(self, value: int) -> None:
        """Set current selection index for compatibility."""
        self.scroll_state.selected = value
        
    @property
    def scroll_offset(self) -> int:
        """Get scroll offset for compatibility."""
        return self.scroll_state.offset
        
    @scroll_offset.setter
    def scroll_offset(self, value: int) -> None:
        """Set scroll offset for compatibility."""
        self.scroll_state.offset = value
        
    def move_up(self) -> None:
        """Move selection up - compatibility method."""
        self.scroll_state.move_up()
        
    def move_down(self) -> None:
        """Move selection down - compatibility method."""
        self.scroll_state.move_down(len(self.items))
        
    def page_up(self) -> None:
        """Move up by one page - compatibility method."""
        page_size = self.dims.height - UI_CONSTANTS['HEADER_HEIGHT'] - UI_CONSTANTS['BORDER_HEIGHT']
        self.scroll_state.page_up(page_size)
        
    def page_down(self) -> None:
        """Move down by one page - compatibility method."""
        page_size = self.dims.height - UI_CONSTANTS['HEADER_HEIGHT'] - UI_CONSTANTS['BORDER_HEIGHT']
        self.scroll_state.page_down(len(self.items), page_size)
        
    def _adjust_scroll(self) -> None:
        """Adjust scroll - compatibility method."""
        visible_lines = self.dims.height - UI_CONSTANTS['HEADER_HEIGHT'] - UI_CONSTANTS['BORDER_HEIGHT']
        self.scroll_state.adjust_offset(visible_lines)

    def draw(self) -> None:
        """Draw the conversation list using base class functionality."""
        try:
            # Build header
            header = f"Conversations ({len(self.filtered_conversations)})"
            if self.search_term:
                header += f" - Filtered by: '{self.search_term}'"
            
            # Use base class to draw items
            self.draw_items(header)
            
        except curses.error:
            pass  # Ignore drawing errors at screen boundaries
    
    def format_item(self, item: Conversation, index: int, is_selected: bool) -> str:
        """Format a conversation for display."""
        prefix = TREE_CHARS["SELECTION_INDICATOR"] + " " if is_selected else "  "
        title = item.title
        msg_count = f" ({item.message_count})"
        
        # Calculate available width
        max_title_width = self.width - len(prefix) - len(msg_count) - 4
        if len(title) > max_title_width:
            title = UIFormatter.truncate_text(title, max_title_width)
        
        return f"{prefix}{title}{msg_count}"


class ConversationDetailView:
    """Manages the conversation detail view."""
    
    def __init__(self, stdscr, dimensions: WindowDimensions):
        self.stdscr = stdscr
        self.dims = dimensions
        self.conversation: Optional[Conversation] = None
        self.scroll_offset = 0
        self.formatted_messages: List[Tuple[MessageRole, List[str]]] = []
        
    def set_conversation(self, conversation: Conversation) -> None:
        """Set the conversation to display."""
        self.conversation = conversation
        self.scroll_offset = 0
        self._format_messages()

    def scroll_up(self) -> None:
        """Scroll up in the message view."""
        if self.scroll_offset > 0:
            self.scroll_offset -= 1

    def scroll_down(self) -> None:
        """Scroll down in the message view."""
        total_lines = sum(len(lines) + 2 for _, lines in self.formatted_messages)  # +2 for role header and blank line
        visible_lines = self.dims.height - 2
        max_scroll = max(0, total_lines - visible_lines)
        
        if self.scroll_offset < max_scroll:
            self.scroll_offset += 1

    def page_up(self) -> None:
        """Page up in the message view."""
        page_size = self.dims.height - 2
        self.scroll_offset = max(0, self.scroll_offset - page_size)

    def page_down(self) -> None:
        """Page down in the message view."""
        page_size = self.dims.height - 2
        total_lines = sum(len(lines) + 2 for _, lines in self.formatted_messages)
        visible_lines = self.dims.height - 2
        max_scroll = max(0, total_lines - visible_lines)
        
        self.scroll_offset = min(max_scroll, self.scroll_offset + page_size)

    def _format_messages(self) -> None:
        """Format messages for display."""
        if not self.conversation:
            self.formatted_messages = []
            return
            
        self.formatted_messages = []
        content_width = self.dims.width - 4  # Leave margins
        
        for message in self.conversation.messages:
            # Wrap message content
            wrapped_lines = []
            for line in message.content.split('\n'):
                if line.strip():
                    wrapped_lines.extend(textwrap.wrap(line, width=content_width))
                else:
                    wrapped_lines.append("")
            
            self.formatted_messages.append((message.role, wrapped_lines))

    def draw(self) -> None:
        """Draw the conversation detail view."""
        if not self.conversation:
            return
            
        try:
            # Clear the area
            for y in range(self.dims.start_y, self.dims.start_y + self.dims.height):
                self.stdscr.move(y, self.dims.start_x)
                self.stdscr.clrtoeol()

            # Draw header
            header = f"Conversation: {self.conversation.title}"
            self.stdscr.attron(curses.color_pair(ColorPair.HEADER.value))
            self.stdscr.addstr(
                self.dims.start_y, 
                self.dims.start_x, 
                header[:self.dims.width]
            )
            self.stdscr.attroff(curses.color_pair(ColorPair.HEADER.value))

            # Draw messages
            current_line = 0
            y = self.dims.start_y + 1
            visible_lines = self.dims.height - 2
            
            for role, lines in self.formatted_messages:
                # Skip lines before scroll offset
                if current_line < self.scroll_offset:
                    lines_to_skip = min(len(lines) + 2, self.scroll_offset - current_line)
                    current_line += lines_to_skip
                    if lines_to_skip < len(lines) + 2:
                        # Partial message visible
                        remaining_lines = lines[lines_to_skip - 2:] if lines_to_skip >= 2 else lines
                        role_header_shown = lines_to_skip >= 2
                    else:
                        continue
                else:
                    remaining_lines = lines
                    role_header_shown = False
                
                # Draw role header if not shown yet
                if not role_header_shown and y <= self.dims.start_y + visible_lines:
                    role_text = f"{role.value.upper()}:"
                    color = self._get_role_color(role)
                    
                    self.stdscr.attron(curses.color_pair(color))
                    self.stdscr.addstr(y, self.dims.start_x, role_text[:self.dims.width])
                    self.stdscr.attroff(curses.color_pair(color))
                    
                    y += 1
                    current_line += 1
                    
                    if y > self.dims.start_y + visible_lines:
                        break

                # Draw message lines
                for line in remaining_lines:
                    if y > self.dims.start_y + visible_lines:
                        break
                        
                    self.stdscr.addstr(y, self.dims.start_x + 2, line[:self.dims.width - 2])
                    y += 1
                    current_line += 1

                # Add blank line after message
                if y <= self.dims.start_y + visible_lines:
                    y += 1
                    current_line += 1
                else:
                    break

            # Draw scroll indicator if needed
            total_lines = sum(len(lines) + 2 for _, lines in self.formatted_messages)
            if total_lines > visible_lines:
                self._draw_scroll_indicator(total_lines, visible_lines)

        except curses.error:
            pass  # Ignore drawing errors at screen boundaries

    def _get_role_color(self, role: MessageRole) -> int:
        """Get color for a message role."""
        role_colors = {
            MessageRole.USER: ColorPair.USER_MESSAGE.value,
            MessageRole.ASSISTANT: ColorPair.ASSISTANT_MESSAGE.value,
            MessageRole.SYSTEM: ColorPair.SYSTEM_MESSAGE.value,
        }
        return role_colors.get(role, ColorPair.DEFAULT.value)

    def _draw_scroll_indicator(self, total_lines: int, visible_lines: int) -> None:
        """Draw a scroll indicator."""
        if self.dims.width < 3:
            return
            
        scroll_ratio = self.scroll_offset / max(1, total_lines - visible_lines)
        scroll_position = int(scroll_ratio * (visible_lines - 1))
        
        x = self.dims.start_x + self.dims.width - 1
        
        for i in range(visible_lines):
            y = self.dims.start_y + 1 + i
            char = TREE_CHARS["SCROLL_BAR_FILLED"] if i == scroll_position else TREE_CHARS["SCROLL_BAR_EMPTY"]
            try:
                self.stdscr.addstr(y, x, char)
            except curses.error:
                pass


class SearchView:
    """Manages the search interface."""
    
    def __init__(self, stdscr, dimensions: WindowDimensions):
        self.stdscr = stdscr
        self.dims = dimensions
        self.search_term = ""
        self.cursor_pos = 0

    def handle_char(self, ch: int) -> bool:
        """
        Handle character input for search.
        
        Returns:
            True if the search term was modified
        """
        if ch == curses.KEY_BACKSPACE or ch == 127 or ch == 8:
            if self.cursor_pos > 0:
                self.search_term = (
                    self.search_term[:self.cursor_pos - 1] + 
                    self.search_term[self.cursor_pos:]
                )
                self.cursor_pos -= 1
                return True
        elif ch == curses.KEY_LEFT:
            self.cursor_pos = max(0, self.cursor_pos - 1)
        elif ch == curses.KEY_RIGHT:
            self.cursor_pos = min(len(self.search_term), self.cursor_pos + 1)
        elif ch == curses.KEY_HOME:
            self.cursor_pos = 0
        elif ch == curses.KEY_END:
            self.cursor_pos = len(self.search_term)
        elif 32 <= ch <= 126:  # Printable ASCII
            char = chr(ch)
            self.search_term = (
                self.search_term[:self.cursor_pos] + 
                char + 
                self.search_term[self.cursor_pos:]
            )
            self.cursor_pos += 1
            return True
        
        return False

    def clear(self) -> None:
        """Clear the search term."""
        self.search_term = ""
        self.cursor_pos = 0

    def draw(self) -> None:
        """Draw the search interface."""
        try:
            # Clear the area
            for y in range(self.dims.start_y, self.dims.start_y + self.dims.height):
                self.stdscr.move(y, self.dims.start_x)
                self.stdscr.clrtoeol()

            # Draw search prompt
            prompt = "Search: "
            self.stdscr.attron(curses.color_pair(ColorPair.HEADER.value))
            self.stdscr.addstr(self.dims.start_y, self.dims.start_x, prompt)
            self.stdscr.attroff(curses.color_pair(ColorPair.HEADER.value))

            # Draw search term
            search_x = self.dims.start_x + len(prompt)
            max_width = self.dims.width - len(prompt) - 1
            
            display_term = self.search_term
            display_cursor = self.cursor_pos
            
            # Handle horizontal scrolling if search term is too long
            if len(display_term) > max_width:
                if self.cursor_pos > max_width - 1:
                    start_offset = self.cursor_pos - max_width + 1
                    display_term = display_term[start_offset:]
                    display_cursor = max_width - 1
                else:
                    display_term = display_term[:max_width]

            self.stdscr.addstr(self.dims.start_y, search_x, display_term)
            
            # Position cursor
            cursor_x = search_x + display_cursor
            if cursor_x < self.dims.start_x + self.dims.width:
                self.stdscr.move(self.dims.start_y, cursor_x)

        except curses.error:
            pass


class HelpView:
    """Displays help information."""
    
    def __init__(self, stdscr, dimensions: WindowDimensions):
        self.stdscr = stdscr
        self.dims = dimensions
        
    def draw(self) -> None:
        """Draw the help screen."""
        help_text = [
            "ChatGPT History Browser - Help",
            "",
            "Navigation:",
            "  ↑/↓ or j/k    - Move selection up/down",
            "  Page Up/Down  - Page up/down",
            "  Home/End      - Go to first/last item",
            "",
            "Actions:",
            "  Enter         - View selected conversation",
            "  /             - Start search",
            "  Esc           - Cancel search / Go back",
            "  q             - Quit application",
            "  h or F1       - Show this help",
            "",
            "Search Mode:",
            "  Type to search conversation titles",
            "  Enter         - Apply search filter",
            "  Esc           - Cancel search",
            "",
            "Conversation View:",
            "  ↑/↓ or j/k    - Scroll up/down",
            "  Page Up/Down  - Page up/down",
            "  Esc or q      - Return to list",
            "",
            "Tips:",
            "  - Search is case-insensitive",
            "  - Use scroll indicators on the right",
            "  - Conversation titles show message count",
        ]
        
        try:
            # Clear the area
            for y in range(self.dims.start_y, self.dims.start_y + self.dims.height):
                self.stdscr.move(y, self.dims.start_x)
                self.stdscr.clrtoeol()

            # Draw help text
            for i, line in enumerate(help_text):
                y = self.dims.start_y + i
                if y >= self.dims.start_y + self.dims.height:
                    break
                    
                if i == 0:  # Title
                    self.stdscr.attron(curses.color_pair(ColorPair.HEADER.value))
                    self.stdscr.addstr(y, self.dims.start_x, line[:self.dims.width])
                    self.stdscr.attroff(curses.color_pair(ColorPair.HEADER.value))
                else:
                    self.stdscr.addstr(y, self.dims.start_x, line[:self.dims.width])

        except curses.error:
            pass


class TreeListView:
    """Manages the conversation tree view with hierarchical folders."""
    
    def __init__(self, stdscr, dimensions: WindowDimensions):
        self.stdscr = stdscr
        self.dims = dimensions
        self.tree_items: List[Tuple[TreeNode, Optional[Conversation], int]] = []  # (node, conversation, depth)
        self.current_index = 0
        self.scroll_offset = 0
        self.search_term = ""
        
    def set_tree_items(self, organized_conversations: List[Tuple[TreeNode, Optional[Conversation]]]) -> None:
        """Set the tree items to display with depth calculation."""
        self.tree_items = []
        
        # Calculate depth for each item based on its path
        for node, conversation in organized_conversations:
            # Count path separators to determine depth
            depth = node.path.count('/') - 1 if node.path.startswith('/') else 0
            depth = max(0, depth)  # Ensure non-negative
            
            # For conversations, they're at the same level as their parent folder
            if node.node_type == NodeType.CONVERSATION and node.parent_id:
                depth = max(0, depth)
            
            self.tree_items.append((node, conversation, depth))
            
        self.current_index = 0
        self.scroll_offset = 0

    def filter_tree_items(self, search_term: str) -> None:
        """Filter tree items based on search term."""
        # Note: For simplicity, we'll just store the search term
        # In a full implementation, this would filter the tree while maintaining structure
        self.search_term = search_term.lower()
        self.current_index = 0
        self.scroll_offset = 0

    def move_up(self) -> None:
        """Move selection up."""
        if self.current_index > 0:
            self.current_index -= 1
            self._adjust_scroll()

    def move_down(self) -> None:
        """Move selection down."""
        if self.current_index < len(self.tree_items) - 1:
            self.current_index += 1
            self._adjust_scroll()

    def page_up(self) -> None:
        """Move up by one page."""
        page_size = self.dims.height - 2
        self.current_index = max(0, self.current_index - page_size)
        self._adjust_scroll()

    def page_down(self) -> None:
        """Move down by one page."""
        page_size = self.dims.height - 2
        max_index = len(self.tree_items) - 1
        self.current_index = min(max_index, self.current_index + page_size)
        self._adjust_scroll()

    def get_selected_item(self) -> Optional[Tuple[TreeNode, Optional[Conversation]]]:
        """Get the currently selected tree item."""
        if 0 <= self.current_index < len(self.tree_items):
            node, conversation, _ = self.tree_items[self.current_index]
            return (node, conversation)
        return None

    def toggle_folder(self) -> bool:
        """
        Toggle folder expansion/collapse.
        
        Returns:
            True if a folder was toggled, False otherwise
        """
        if 0 <= self.current_index < len(self.tree_items):
            node, _, _ = self.tree_items[self.current_index]
            if node.node_type == NodeType.FOLDER:
                node.expanded = not node.expanded
                return True
        return False

    def _adjust_scroll(self) -> None:
        """Adjust scroll offset to keep selection visible."""
        visible_lines = self.dims.height - 2
        
        if self.current_index < self.scroll_offset:
            self.scroll_offset = self.current_index
        elif self.current_index >= self.scroll_offset + visible_lines:
            self.scroll_offset = self.current_index - visible_lines + 1

    def draw(self) -> None:
        """Draw the tree view."""
        try:
            # Clear the area
            for y in range(self.dims.start_y, self.dims.start_y + self.dims.height):
                self.stdscr.move(y, self.dims.start_x)
                self.stdscr.clrtoeol()

            # Draw header
            header = f"Conversation Tree ({len(self.tree_items)})"
            if self.search_term:
                header += f" - Filtered by: '{self.search_term}'"
            
            self.stdscr.attron(curses.color_pair(ColorPair.HEADER.value))
            self.stdscr.addstr(
                self.dims.start_y, 
                self.dims.start_x, 
                header[:self.dims.width]
            )
            self.stdscr.attroff(curses.color_pair(ColorPair.HEADER.value))

            # Draw tree items
            visible_lines = self.dims.height - 2
            for i in range(visible_lines):
                list_index = self.scroll_offset + i
                if list_index >= len(self.tree_items):
                    break

                y = self.dims.start_y + 1 + i
                node, conversation, depth = self.tree_items[list_index]
                
                # Create tree visualization
                indent = TREE_CHARS["TREE_INDENT"] * depth
                
                if node.node_type == NodeType.FOLDER:
                    # Folder with expand/collapse indicator
                    expand_char = TREE_CHARS["FOLDER_EXPANDED"] if node.expanded else TREE_CHARS["FOLDER_COLLAPSED"]
                    folder_icon = TREE_CHARS["FOLDER_ICON"]
                    prefix = f"{indent}{expand_char} {folder_icon} "
                    name = node.name
                    
                    # Show folder with child count
                    child_count = len(node.children)
                    if child_count > 0:
                        name += f" ({child_count})"
                        
                    color = ColorPair.FOLDER.value
                else:
                    # Conversation
                    conv_icon = TREE_CHARS["CONVERSATION_ICON"]
                    prefix = f"{indent}  {conv_icon} "
                    
                    # Use custom title or conversation title
                    if conversation:
                        name = node.name if node.name != node.id else conversation.title
                        msg_count = f" ({conversation.message_count})"
                        name += msg_count
                    else:
                        name = f"{node.name} [Not Found]"
                        
                    color = ColorPair.CONVERSATION_TREE.value

                # Selection indicator
                if list_index == self.current_index:
                    prefix = TREE_CHARS["SELECTION_INDICATOR"] + " " + prefix[2:]
                else:
                    prefix = "  " + prefix[2:]

                # Truncate if necessary
                max_width = self.dims.width - len(prefix) - 1
                if len(name) > max_width:
                    name = name[:max_width - 3] + "..."
                
                line = f"{prefix}{name}"
                
                # Apply selection highlighting
                if list_index == self.current_index:
                    self.stdscr.attron(curses.color_pair(ColorPair.SELECTED.value))
                    self.stdscr.addstr(y, self.dims.start_x, line[:self.dims.width])
                    self.stdscr.attroff(curses.color_pair(ColorPair.SELECTED.value))
                else:
                    self.stdscr.attron(curses.color_pair(color))
                    self.stdscr.addstr(y, self.dims.start_x, line[:self.dims.width])
                    self.stdscr.attroff(curses.color_pair(color))

            # Draw scroll indicator if needed
            if len(self.tree_items) > visible_lines:
                self._draw_scroll_indicator()

        except curses.error:
            pass

    def _draw_scroll_indicator(self) -> None:
        """Draw a scroll indicator on the right side."""
        if self.dims.width < 3:
            return
            
        visible_lines = self.dims.height - 2
        total_lines = len(self.tree_items)
        
        if total_lines <= visible_lines:
            return
            
        # Calculate scroll bar position
        scroll_ratio = self.scroll_offset / (total_lines - visible_lines)
        scroll_position = int(scroll_ratio * (visible_lines - 1))
        
        x = self.dims.start_x + self.dims.width - 1
        
        for i in range(visible_lines):
            y = self.dims.start_y + 1 + i
            char = TREE_CHARS["SCROLL_BAR_FILLED"] if i == scroll_position else TREE_CHARS["SCROLL_BAR_EMPTY"]
            try:
                self.stdscr.addstr(y, x, char)
            except curses.error:
                pass


class ChatGPTTUI:
    """Main TUI application class."""
    
    def __init__(self, conversations_path: Optional[str] = None, debug: bool = False):
        self.conversations_path = conversations_path
        self.debug = debug
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Application state
        self.mode = ViewMode.CONVERSATION_LIST
        self.conversations: List[Conversation] = []
        self.running = True
        
        # UI components (initialized in _init_ui)
        self.stdscr = None
        self.status_bar: Optional[StatusBar] = None
        self.list_view: Optional[ConversationListView] = None
        self.tree_view: Optional[TreeListView] = None
        self.detail_view: Optional[ConversationDetailView] = None
        self.search_view: Optional[SearchView] = None
        self.help_view: Optional[HelpView] = None
        
        # Services
        self.loader = ConversationLoader(debug=debug)
        self.searcher = ConversationSearcher(debug=debug)
        self.organizer: Optional[ConversationOrganizer] = None

    def run(self) -> None:
        """Run the TUI application."""
        try:
            curses.wrapper(self._main)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            if self.debug:
                raise
            print(f"Error: {e}")

    def _main(self, stdscr) -> None:
        """Main curses application loop."""
        self.stdscr = stdscr
        
        try:
            self._init_curses()
            self._init_ui()
            self._load_conversations()
            self._main_loop()
        except Exception as e:
            if self.debug:
                self.logger.exception("Error in main loop")
                raise
            self.status_bar.show_message(f"Error: {e}", is_error=True)
            self.stdscr.getch()  # Wait for user input before exiting

    def _init_curses(self) -> None:
        """Initialize curses settings."""
        # Basic curses setup
        curses.curs_set(0)  # Hide cursor
        self.stdscr.keypad(True)  # Enable special keys
        curses.noecho()  # Don't echo keys
        curses.cbreak()  # React to keys immediately
        
        # Initialize colors if available
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            
            # Define color pairs
            curses.init_pair(ColorPair.DEFAULT.value, -1, -1)
            curses.init_pair(ColorPair.HEADER.value, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(ColorPair.SELECTED.value, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(ColorPair.BORDER.value, curses.COLOR_BLUE, -1)
            curses.init_pair(ColorPair.STATUS.value, curses.COLOR_WHITE, curses.COLOR_BLACK)
            curses.init_pair(ColorPair.USER_MESSAGE.value, curses.COLOR_GREEN, -1)
            curses.init_pair(ColorPair.ASSISTANT_MESSAGE.value, curses.COLOR_CYAN, -1)
            curses.init_pair(ColorPair.SYSTEM_MESSAGE.value, curses.COLOR_YELLOW, -1)
            curses.init_pair(ColorPair.SEARCH_HIGHLIGHT.value, curses.COLOR_BLACK, curses.COLOR_YELLOW)
            curses.init_pair(ColorPair.ERROR.value, curses.COLOR_WHITE, curses.COLOR_RED)
            curses.init_pair(ColorPair.FOLDER.value, curses.COLOR_BLUE, -1)
            curses.init_pair(ColorPair.CONVERSATION_TREE.value, curses.COLOR_GREEN, -1)

    def _init_ui(self) -> None:
        """Initialize UI components."""
        height, width = self.stdscr.getmaxyx()
        
        # Create status bar at bottom
        self.status_bar = StatusBar(self.stdscr, height - 1, width)
        
        # Create main content area (leave space for status bar)
        content_height = height - 1
        content_dims = WindowDimensions(content_height, width, 0, 0)
        
        # Initialize views
        self.list_view = ConversationListView(self.stdscr, content_dims)
        self.tree_view = TreeListView(self.stdscr, content_dims)
        self.detail_view = ConversationDetailView(self.stdscr, content_dims)
        self.search_view = SearchView(self.stdscr, WindowDimensions(1, width, 0, 0))
        self.help_view = HelpView(self.stdscr, content_dims)

    def _load_conversations(self) -> None:
        """Load conversations from file."""
        try:
            if self.conversations_path:
                path = Path(self.conversations_path)
            else:
                path = Path.home() / '.chatgpt' / 'conversations.json'
                
            self.status_bar.show_message("Loading conversations...")
            self.stdscr.refresh()
            
            self.conversations = self.loader.load_conversations(path)
            self.list_view.set_conversations(self.conversations)
            
            # Initialize conversation organizer
            self.organizer = ConversationOrganizer(path, debug=self.debug)
            organized_conversations = self.organizer.get_organized_conversations(self.conversations)
            self.tree_view.set_tree_items(organized_conversations)
            
            if self.conversations:
                self.status_bar.show_message(f"Loaded {len(self.conversations)} conversations")
            else:
                self.status_bar.show_message("No conversations found", is_error=True)
                
        except Exception as e:
            self.status_bar.show_message(f"Failed to load conversations: {e}", is_error=True)

    def _main_loop(self) -> None:
        """Main event loop."""
        while self.running:
            self._draw_current_view()
            self._update_status_bar()
            self.stdscr.refresh()
            
            # Get user input
            try:
                ch = self.stdscr.getch()
                self._handle_input(ch)
            except KeyboardInterrupt:
                self.running = False

    def _draw_current_view(self) -> None:
        """Draw the current view."""
        self.stdscr.clear()
        
        if self.mode == ViewMode.CONVERSATION_LIST:
            self.list_view.draw()
            if hasattr(self, '_search_active') and self._search_active:
                self.search_view.draw()
        elif self.mode == ViewMode.CONVERSATION_TREE:
            self.tree_view.draw()
            if hasattr(self, '_search_active') and self._search_active:
                self.search_view.draw()
        elif self.mode == ViewMode.CONVERSATION_DETAIL:
            self.detail_view.draw()
        elif self.mode == ViewMode.HELP:
            self.help_view.draw()

    def _update_status_bar(self) -> None:
        """Update the status bar with current shortcuts."""
        shortcuts = self._get_current_shortcuts()
        self.status_bar.show_shortcuts(shortcuts)

    def _get_current_shortcuts(self) -> Dict[str, str]:
        """Get shortcuts for the current mode."""
        base_shortcuts = {"q": "quit", "h": "help", "t": "tree", "l": "list"}
        
        if self.mode == ViewMode.CONVERSATION_LIST:
            if hasattr(self, '_search_active') and self._search_active:
                return {"Enter": "search", "Esc": "cancel", **base_shortcuts}
            else:
                return {"Enter": "view", "/": "search", "↑↓": "navigate", **base_shortcuts}
        elif self.mode == ViewMode.CONVERSATION_TREE:
            if hasattr(self, '_search_active') and self._search_active:
                return {"Enter": "search", "Esc": "cancel", **base_shortcuts}
            else:
                return {"Enter": "view", "Space": "toggle", "/": "search", "↑↓": "navigate", **base_shortcuts}
        elif self.mode == ViewMode.CONVERSATION_DETAIL:
            return {"Esc": "back", "↑↓": "scroll", "PgUp/Dn": "page", **base_shortcuts}
        elif self.mode == ViewMode.HELP:
            return {"Esc": "back", **base_shortcuts}
        
        return base_shortcuts

    def _handle_input(self, ch: int) -> None:
        """Handle user input based on current mode."""
        # Global shortcuts
        if ch == ord('q'):
            if (self.mode == ViewMode.CONVERSATION_LIST or self.mode == ViewMode.CONVERSATION_TREE) and not getattr(self, '_search_active', False):
                self.running = False
            else:
                self._go_back()
        elif ch == ord('h') or ch == curses.KEY_F1:
            self._show_help()
        elif ch == ord('t'):
            self._switch_to_tree_view()
        elif ch == ord('l'):
            self._switch_to_list_view()
        elif ch == 27:  # ESC
            self._go_back()
        elif self.mode == ViewMode.CONVERSATION_LIST:
            self._handle_list_input(ch)
        elif self.mode == ViewMode.CONVERSATION_TREE:
            self._handle_tree_input(ch)
        elif self.mode == ViewMode.CONVERSATION_DETAIL:
            self._handle_detail_input(ch)

    def _handle_list_input(self, ch: int) -> None:
        """Handle input in conversation list mode."""
        if hasattr(self, '_search_active') and self._search_active:
            # Search mode
            if ch == 10 or ch == 13:  # Enter
                self._apply_search()
            elif self.search_view.handle_char(ch):
                # Update filter in real-time
                self.list_view.filter_conversations(self.search_view.search_term)
        else:
            # Normal list navigation
            if ch == curses.KEY_UP or ch == ord('k'):
                self.list_view.move_up()
            elif ch == curses.KEY_DOWN or ch == ord('j'):
                self.list_view.move_down()
            elif ch == curses.KEY_PPAGE:
                self.list_view.page_up()
            elif ch == curses.KEY_NPAGE:
                self.list_view.page_down()
            elif ch == curses.KEY_HOME:
                self.list_view.current_index = 0
                self.list_view._adjust_scroll()
            elif ch == curses.KEY_END:
                self.list_view.current_index = len(self.list_view.filtered_conversations) - 1
                self.list_view._adjust_scroll()
            elif ch == 10 or ch == 13:  # Enter
                self._view_selected_conversation()
            elif ch == ord('/'):
                self._start_search()

    def _handle_tree_input(self, ch: int) -> None:
        """Handle input in conversation tree mode."""
        if hasattr(self, '_search_active') and self._search_active:
            # Search mode
            if ch == 10 or ch == 13:  # Enter
                self._apply_search_tree()
            elif self.search_view.handle_char(ch):
                # Update filter in real-time
                self.tree_view.filter_tree_items(self.search_view.search_term)
        else:
            # Normal tree navigation
            if ch == curses.KEY_UP or ch == ord('k'):
                self.tree_view.move_up()
            elif ch == curses.KEY_DOWN or ch == ord('j'):
                self.tree_view.move_down()
            elif ch == curses.KEY_PPAGE:
                self.tree_view.page_up()
            elif ch == curses.KEY_NPAGE:
                self.tree_view.page_down()
            elif ch == curses.KEY_HOME:
                self.tree_view.current_index = 0
                self.tree_view._adjust_scroll()
            elif ch == curses.KEY_END:
                self.tree_view.current_index = len(self.tree_view.tree_items) - 1
                self.tree_view._adjust_scroll()
            elif ch == 10 or ch == 13:  # Enter
                self._view_selected_tree_item()
            elif ch == ord(' '):  # Space
                self._toggle_tree_folder()
            elif ch == ord('/'):
                self._start_search()

    def _handle_detail_input(self, ch: int) -> None:
        """Handle input in conversation detail mode."""
        if ch == curses.KEY_UP or ch == ord('k'):
            self.detail_view.scroll_up()
        elif ch == curses.KEY_DOWN or ch == ord('j'):
            self.detail_view.scroll_down()
        elif ch == curses.KEY_PPAGE:
            self.detail_view.page_up()
        elif ch == curses.KEY_NPAGE:
            self.detail_view.page_down()

    def _start_search(self) -> None:
        """Start search mode."""
        self._search_active = True
        self.search_view.clear()
        curses.curs_set(1)  # Show cursor in search mode

    def _apply_search(self) -> None:
        """Apply the current search."""
        self._search_active = False
        curses.curs_set(0)  # Hide cursor
        self.list_view.filter_conversations(self.search_view.search_term)

    def _apply_search_tree(self) -> None:
        """Apply the current search to tree view."""
        self._search_active = False
        curses.curs_set(0)  # Hide cursor
        self.tree_view.filter_tree_items(self.search_view.search_term)

    def _view_selected_conversation(self) -> None:
        """View the selected conversation."""
        conversation = self.list_view.get_selected_conversation()
        if conversation:
            self.detail_view.set_conversation(conversation)
            self.mode = ViewMode.CONVERSATION_DETAIL

    def _view_selected_tree_item(self) -> None:
        """View the selected tree item."""
        item = self.tree_view.get_selected_item()
        if item:
            node, conversation = item
            if conversation:  # It's a conversation
                self.detail_view.set_conversation(conversation)
                self.mode = ViewMode.CONVERSATION_DETAIL

    def _toggle_tree_folder(self) -> None:
        """Toggle folder expansion in tree view."""
        if self.tree_view.toggle_folder():
            # Refresh tree display with updated expansion state
            if self.organizer:
                organized_conversations = self.organizer.get_organized_conversations(self.conversations)
                self.tree_view.set_tree_items(organized_conversations)

    def _switch_to_tree_view(self) -> None:
        """Switch to tree view mode."""
        self.mode = ViewMode.CONVERSATION_TREE

    def _switch_to_list_view(self) -> None:
        """Switch to list view mode."""
        self.mode = ViewMode.CONVERSATION_LIST

    def _show_help(self) -> None:
        """Show the help screen."""
        self.mode = ViewMode.HELP

    def _go_back(self) -> None:
        """Go back to the previous view."""
        if hasattr(self, '_search_active') and self._search_active:
            self._search_active = False
            curses.curs_set(0)
            self.search_view.clear()
            if self.mode == ViewMode.CONVERSATION_LIST:
                self.list_view.filter_conversations("")  # Clear filter
            elif self.mode == ViewMode.CONVERSATION_TREE:
                self.tree_view.filter_tree_items("")  # Clear filter
        elif self.mode == ViewMode.CONVERSATION_DETAIL:
            self.mode = ViewMode.CONVERSATION_LIST
        elif self.mode == ViewMode.HELP:
            self.mode = ViewMode.CONVERSATION_LIST
        elif self.mode == ViewMode.CONVERSATION_LIST:
            self.running = False
        elif self.mode == ViewMode.CONVERSATION_TREE:
            self.running = False


def main() -> None:
    """Main entry point for the TUI."""
    
    parser = argparse.ArgumentParser(description="ChatGPT History Browser TUI")
    parser.add_argument("--path", help="Path to conversations.json file")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    tui = ChatGPTTUI(conversations_path=args.path, debug=args.debug)
    tui.run()


if __name__ == "__main__":
    main()