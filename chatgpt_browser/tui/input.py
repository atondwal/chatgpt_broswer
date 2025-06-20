#!/usr/bin/env python3
"""Simple input dialogs for TUI."""

import curses
from typing import Optional


def get_input(stdscr, prompt: str, initial: str = "") -> Optional[str]:
    """Get text input from user."""
    height, width = stdscr.getmaxyx()
    
    # Create centered window
    win_height = 5
    win_width = min(60, width - 4)
    y = (height - win_height) // 2
    x = (width - win_width) // 2
    
    win = curses.newwin(win_height, win_width, y, x)
    win.keypad(True)  # Enable special keys
    win.border()
    
    # Show prompt
    win.addstr(1, 2, prompt[:win_width - 4])
    win.addstr(3, 2, "ESC: Cancel, Enter: OK")
    
    # Edit loop
    text = initial
    cursor = len(text)
    
    while True:
        # Show text
        win.move(2, 2)
        win.clrtoeol()
        display_text = text[max(0, cursor - win_width + 7):][:win_width - 4]
        win.addstr(2, 2, display_text)
        
        # Position cursor
        cursor_x = min(cursor, win_width - 7) + 2
        win.move(2, cursor_x)
        win.refresh()
        
        # Handle input
        key = win.getch()
        
        if key == 27:  # ESC
            return None
        elif key in (10, 13):  # Enter
            return text.strip() or None
        elif key in (curses.KEY_BACKSPACE, 127):
            if cursor > 0:
                text = text[:cursor-1] + text[cursor:]
                cursor -= 1
        elif key == curses.KEY_LEFT:
            cursor = max(0, cursor - 1)
        elif key == curses.KEY_RIGHT:
            cursor = min(len(text), cursor + 1)
        elif 32 <= key <= 126:  # Printable
            text = text[:cursor] + chr(key) + text[cursor:]
            cursor += 1


def confirm(stdscr, message: str) -> bool:
    """Show yes/no confirmation dialog."""
    height, width = stdscr.getmaxyx()
    
    # Create centered window
    win_height = 5
    win_width = min(50, width - 4)
    y = (height - win_height) // 2
    x = (width - win_width) // 2
    
    win = curses.newwin(win_height, win_width, y, x)
    win.keypad(True)  # Enable special keys
    win.border()
    
    # Show message
    win.addstr(1, 2, message[:win_width - 4])
    win.addstr(2, 2, "y = Yes, n/ESC = No")
    win.refresh()
    
    # Wait for response
    while True:
        key = win.getch()
        if key in (ord('y'), ord('Y')):
            return True
        elif key in (ord('n'), ord('N'), 27):
            return False


def select_folder(stdscr, tree_items: list) -> Optional[str]:
    """Let user select a folder."""
    # Filter folders
    folders = [(node, depth) for node, _, depth in tree_items if node.is_folder]
    if not folders:
        return None
        
    height, width = stdscr.getmaxyx()
    
    # Create selection window
    win_height = min(15, height - 4)
    win_width = min(60, width - 4)
    y = (height - win_height) // 2
    x = (width - win_width) // 2
    
    win = curses.newwin(win_height, win_width, y, x)
    win.keypad(True)  # Enable special keys
    
    # Add root option
    options = [(None, 0)] + folders  # None = root
    selected = 0
    offset = 0
    
    while True:
        win.clear()
        win.border()
        win.addstr(1, 2, "Select destination:")
        
        # Show folders
        visible_height = win_height - 4
        
        # Adjust offset
        if selected < offset:
            offset = selected
        elif selected >= offset + visible_height:
            offset = selected - visible_height + 1
            
        for i in range(visible_height):
            idx = offset + i
            if idx >= len(options):
                break
                
            node, depth = options[idx]
            
            # Format name
            if node is None:
                name = "📁 <Root>"
            else:
                name = "  " * depth + "📁 " + node.name
                
            # Truncate if needed
            if len(name) > win_width - 6:
                name = name[:win_width - 9] + "..."
                
            # Highlight selection
            attr = curses.A_REVERSE if idx == selected else 0
            win.addstr(2 + i, 2, name, attr)
            
        win.addstr(win_height - 2, 2, "↑/↓: Move, Enter: Select, ESC: Cancel")
        win.refresh()
        
        # Handle input
        key = win.getch()
        
        if key == 27:  # ESC
            return None
        elif key in (10, 13):  # Enter
            node, _ = options[selected]
            return None if node is None else node.id
        elif key == curses.KEY_UP:
            selected = max(0, selected - 1)
        elif key == curses.KEY_DOWN:
            selected = min(len(options) - 1, selected + 1)