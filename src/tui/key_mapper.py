#!/usr/bin/env python3
"""Map escape sequences to function keys for better terminal compatibility."""

import curses

# Common escape sequences for function keys
FUNCTION_KEY_SEQUENCES = {
    # F1-F5 escape sequences (common terminals)
    '\x1b[11~': curses.KEY_F1,    # F1
    '\x1b[12~': curses.KEY_F2,    # F2
    '\x1b[13~': curses.KEY_F3,    # F3
    '\x1b[14~': curses.KEY_F4,    # F4
    '\x1b[15~': curses.KEY_F5,    # F5
    
    # Alternative F1-F5 sequences
    '\x1bOP': curses.KEY_F1,      # F1 (xterm)
    '\x1bOQ': curses.KEY_F2,      # F2 (xterm)
    '\x1bOR': curses.KEY_F3,      # F3 (xterm)
    '\x1bOS': curses.KEY_F4,      # F4 (xterm)
    '\x1b[15~': curses.KEY_F5,    # F5 (xterm)
    
    # macOS Terminal.app sequences
    '\x1b[1P': curses.KEY_F1,     # F1 (Terminal.app)
    '\x1b[1Q': curses.KEY_F2,     # F2 (Terminal.app)
    '\x1b[1R': curses.KEY_F3,     # F3 (Terminal.app)
    '\x1b[1S': curses.KEY_F4,     # F4 (Terminal.app)
}

def get_key_with_escape_handling(stdscr, timeout_ms=50):
    """
    Get a key from stdscr, handling escape sequences.
    
    Returns the key code, mapping escape sequences to function keys.
    """
    # Set a short timeout for escape sequences
    stdscr.timeout(timeout_ms)
    
    key = stdscr.getch()
    
    # If we got ESC, check for a sequence
    if key == 27:  # ESC
        sequence = '\x1b'
        
        # Read up to 5 more characters for the sequence
        for _ in range(5):
            next_key = stdscr.getch()
            if next_key == -1:  # Timeout
                break
            sequence += chr(next_key)
            
            # Check if we have a complete sequence
            if sequence in FUNCTION_KEY_SEQUENCES:
                stdscr.timeout(-1)  # Reset timeout
                return FUNCTION_KEY_SEQUENCES[sequence]
        
        # If no match, return ESC
        stdscr.timeout(-1)  # Reset timeout
        return 27
    
    # Reset timeout and return the key
    stdscr.timeout(-1)
    return key