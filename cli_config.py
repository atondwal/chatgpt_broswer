#!/usr/bin/env python3
"""
Configuration module for the legacy CLI interface.

Centralizes paths, default settings, and configuration management.
"""

import os
from pathlib import Path

# Default paths and settings
HISTORY_PATH = os.path.expanduser('~/.chatgpt/conversations.json')

# Alternative history paths to try if default doesn't exist
ALTERNATIVE_PATHS = [
    os.path.expanduser('~/Downloads/conversations.json'),
    './conversations.json',
    '../conversations.json'
]

# Display settings
DEFAULT_TERMINAL_WIDTH = 80
MAX_CONTEXT_LENGTH = 200  # For search results

# UI settings for curses interface
UI_SETTINGS = {
    'hide_cursor': True,
    'enable_keypad': True,
    'refresh_on_resize': True
}

def find_conversations_file():
    """
    Find the conversations.json file in standard locations.
    
    Returns:
        str: Path to conversations file if found, None otherwise
    """
    # Try default path first
    if os.path.exists(HISTORY_PATH):
        return HISTORY_PATH
    
    # Try alternative paths
    for path in ALTERNATIVE_PATHS:
        if os.path.exists(path):
            return path
    
    return None

def get_output_path(input_path: str, suffix: str = "_export") -> str:
    """
    Generate an output file path based on input file.
    
    Args:
        input_path: Input file path
        suffix: Suffix to add before file extension
        
    Returns:
        str: Output file path
    """
    path = Path(input_path)
    return str(path.parent / f"{path.stem}{suffix}{path.suffix}")