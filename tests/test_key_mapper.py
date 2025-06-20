#!/usr/bin/env python3
"""Test key mapper functionality."""

import curses
from unittest.mock import Mock
from chatgpt_browser.tui.key_mapper import get_key_with_escape_handling

def test_escape_sequences():
    """Test that escape sequences are properly mapped to function keys."""
    # Mock stdscr
    stdscr = Mock()
    
    # Test F1 sequence (\x1b[11~)
    stdscr.getch.side_effect = [27, ord('['), ord('1'), ord('1'), ord('~')]
    key = get_key_with_escape_handling(stdscr)
    assert key == curses.KEY_F1
    
    # Test F2 sequence (\x1b[12~)
    stdscr.getch.side_effect = [27, ord('['), ord('1'), ord('2'), ord('~')]
    key = get_key_with_escape_handling(stdscr)
    assert key == curses.KEY_F2
    
    # Test plain ESC (timeout after ESC)
    stdscr.getch.side_effect = [27, -1]  # -1 means timeout
    key = get_key_with_escape_handling(stdscr)
    assert key == 27  # Should return ESC
    
    # Test normal key
    stdscr.getch.side_effect = [ord('a')]
    key = get_key_with_escape_handling(stdscr)
    assert key == ord('a')
    
    print("All key mapper tests passed!")

if __name__ == "__main__":
    test_escape_sequences()