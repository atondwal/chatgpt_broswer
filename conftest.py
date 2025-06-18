#!/usr/bin/env python3
"""
Pytest configuration file to fix module import issues.

This ensures that the 'src' module can be imported when running pytest directly.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))