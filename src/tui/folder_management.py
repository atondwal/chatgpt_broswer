#!/usr/bin/env python3
"""
Folder management utilities for the enhanced TUI.

Provides interactive folder operations like create, rename, delete.
"""

import curses
from typing import Optional, Tuple
from src.tree.tree_constants import UI_CONSTANTS, COLOR_PAIRS
from src.tree.tree_types import NodeType


class FolderManager:
    """Handles interactive folder management operations."""
    
    def __init__(self, stdscr):
        self.stdscr = stdscr
        
    def get_user_input(self, prompt: str, initial_value: str = "", 
                      max_length: int = 50) -> Optional[str]:
        """Get text input from user with a prompt."""
        height, width = self.stdscr.getmaxyx()
        
        # Create input window
        input_height = 5
        input_width = min(60, width - 4)
        start_y = (height - input_height) // 2
        start_x = (width - input_width) // 2
        
        # Create window with border
        win = curses.newwin(input_height, input_width, start_y, start_x)
        win.border()
        
        # Show prompt
        prompt_text = prompt[:input_width - 4]
        win.addstr(1, 2, prompt_text)
        
        # Input area
        input_y = 2
        input_x = 2
        input_field_width = input_width - 4
        
        # Show initial value
        current_text = initial_value[:max_length]
        cursor_pos = len(current_text)
        
        def refresh_input():
            """Refresh the input field display."""
            win.move(input_y, input_x)
            win.clrtoeol()
            
            # Show text with cursor
            display_text = current_text
            if len(display_text) > input_field_width - 1:
                # Scroll text if too long
                start_idx = max(0, cursor_pos - input_field_width + 2)
                display_text = display_text[start_idx:start_idx + input_field_width - 1]
                cursor_display_pos = cursor_pos - start_idx
            else:
                cursor_display_pos = cursor_pos
            
            win.addstr(input_y, input_x, display_text)
            
            # Position cursor
            win.move(input_y, input_x + cursor_display_pos)
            win.refresh()
        
        # Show cancel instruction
        win.addstr(3, 2, "Press ESC to cancel, Enter to confirm")
        
        # Initial display
        refresh_input()
        
        # Input loop
        while True:
            try:
                key = win.getch()
                
                if key == 27:  # ESC
                    return None
                elif key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
                    result = current_text.strip()
                    return result if result else None
                elif key == curses.KEY_BACKSPACE or key == 127:
                    if cursor_pos > 0:
                        current_text = current_text[:cursor_pos-1] + current_text[cursor_pos:]
                        cursor_pos -= 1
                elif key == curses.KEY_LEFT:
                    cursor_pos = max(0, cursor_pos - 1)
                elif key == curses.KEY_RIGHT:
                    cursor_pos = min(len(current_text), cursor_pos + 1)
                elif key == curses.KEY_HOME:
                    cursor_pos = 0
                elif key == curses.KEY_END:
                    cursor_pos = len(current_text)
                elif 32 <= key <= 126:  # Printable characters
                    if len(current_text) < max_length:
                        current_text = current_text[:cursor_pos] + chr(key) + current_text[cursor_pos:]
                        cursor_pos += 1
                
                refresh_input()
                
            except KeyboardInterrupt:
                return None
            except curses.error:
                continue
    
    def confirm_action(self, message: str) -> bool:
        """Show confirmation dialog for destructive actions."""
        height, width = self.stdscr.getmaxyx()
        
        # Create confirmation window
        dialog_height = 5
        dialog_width = min(50, width - 4)
        start_y = (height - dialog_height) // 2
        start_x = (width - dialog_width) // 2
        
        win = curses.newwin(dialog_height, dialog_width, start_y, start_x)
        win.border()
        
        # Show message
        message_text = message[:dialog_width - 4]
        win.addstr(1, 2, message_text)
        
        # Show options
        win.addstr(2, 2, "y/Y = Yes, n/N or ESC = No")
        win.refresh()
        
        while True:
            try:
                key = win.getch()
                
                if key in (ord('y'), ord('Y')):
                    return True
                elif key in (ord('n'), ord('N'), 27):  # n, N, or ESC
                    return False
                    
            except KeyboardInterrupt:
                return False
            except curses.error:
                continue
    
    def show_message(self, message: str, is_error: bool = False) -> None:
        """Show a temporary message to the user."""
        height, width = self.stdscr.getmaxyx()
        
        # Create message window
        dialog_height = 4
        dialog_width = min(max(len(message) + 4, 30), width - 4)
        start_y = (height - dialog_height) // 2
        start_x = (width - dialog_width) // 2
        
        win = curses.newwin(dialog_height, dialog_width, start_y, start_x)
        win.border()
        
        # Choose color
        if is_error:
            color = curses.color_pair(COLOR_PAIRS["ERROR"])
        else:
            color = curses.color_pair(COLOR_PAIRS["STATUS"])
        
        # Show message
        message_text = message[:dialog_width - 4]
        win.addstr(1, 2, message_text, color)
        win.addstr(2, 2, "Press any key to continue")
        win.refresh()
        
        # Wait for key press
        try:
            win.getch()
        except (KeyboardInterrupt, curses.error):
            pass
    
    def select_folder(self, tree_items, current_selection: int) -> Optional[str]:
        """Let user select a folder from the tree for moving items."""
        if not tree_items:
            return None
        
        height, width = self.stdscr.getmaxyx()
        
        # Create selection window
        dialog_height = min(15, height - 4)
        dialog_width = min(60, width - 4)
        start_y = (height - dialog_height) // 2
        start_x = (width - dialog_width) // 2
        
        win = curses.newwin(dialog_height, dialog_width, start_y, start_x)
        win.border()
        
        # Filter to only show folders
        folders = [(i, item) for i, item in enumerate(tree_items) 
                  if item[0].node_type == NodeType.FOLDER]
        folders.insert(0, (-1, (None, None, 0)))  # Add "Root" option
        
        selected_idx = 0
        scroll_offset = 0
        
        def refresh_selection():
            """Refresh the folder selection display."""
            win.clear()
            win.border()
            
            win.addstr(1, 2, "Select destination folder:")
            
            visible_height = dialog_height - 4
            
            # Adjust scroll
            if selected_idx < scroll_offset:
                scroll_offset = selected_idx
            elif selected_idx >= scroll_offset + visible_height:
                scroll_offset = selected_idx - visible_height + 1
            
            # Display folders
            for i in range(visible_height):
                folder_idx = scroll_offset + i
                if folder_idx >= len(folders):
                    break
                
                orig_idx, (tree_node, _, depth) = folders[folder_idx]
                
                # Format folder name
                if orig_idx == -1:  # Root option
                    display_text = "📁 <Root>"
                else:
                    indent = "  " * depth
                    display_text = f"{indent}📁 {tree_node.name}"
                
                # Truncate to fit
                max_text_width = dialog_width - 6
                if len(display_text) > max_text_width:
                    display_text = display_text[:max_text_width-3] + "..."
                
                # Highlight if selected
                attr = curses.A_REVERSE if folder_idx == selected_idx else 0
                
                win.addstr(2 + i, 2, display_text, attr)
            
            # Show instructions
            win.addstr(dialog_height - 2, 2, "↑/↓: Navigate, Enter: Select, ESC: Cancel")
            win.refresh()
        
        refresh_selection()
        
        while True:
            try:
                key = win.getch()
                
                if key == 27:  # ESC
                    return None
                elif key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
                    if folders:
                        orig_idx, (tree_node, _, _) = folders[selected_idx]
                        if orig_idx == -1:
                            return None  # Root selected
                        else:
                            return tree_node.id
                    return None
                elif key == curses.KEY_UP:
                    selected_idx = max(0, selected_idx - 1)
                elif key == curses.KEY_DOWN:
                    selected_idx = min(len(folders) - 1, selected_idx + 1)
                
                refresh_selection()
                
            except KeyboardInterrupt:
                return None
            except curses.error:
                continue


def get_folder_name_input(stdscr, prompt: str = "Enter folder name:", 
                         initial_value: str = "") -> Optional[str]:
    """Convenience function to get folder name input."""
    manager = FolderManager(stdscr)
    return manager.get_user_input(prompt, initial_value, max_length=100)


def confirm_delete(stdscr, item_name: str, item_type: str = "item") -> bool:
    """Convenience function to confirm deletion."""
    manager = FolderManager(stdscr)
    return manager.confirm_action(f"Delete {item_type} '{item_name}'?")


def show_error_message(stdscr, message: str) -> None:
    """Convenience function to show error message."""
    manager = FolderManager(stdscr)
    manager.show_message(message, is_error=True)


def show_success_message(stdscr, message: str) -> None:
    """Convenience function to show success message."""
    manager = FolderManager(stdscr)
    manager.show_message(message, is_error=False)