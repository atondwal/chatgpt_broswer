#!/usr/bin/env python3
"""Main entry point for ChatGPT TUI."""

import sys
import os

# Add parent directory to path so we can import src
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from src.tui.tui import main

if __name__ == "__main__":
    main()