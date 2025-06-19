#!/usr/bin/env python3
"""Main entry point for ChatGPT TUI."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.tui.tui import main

if __name__ == "__main__":
    main()