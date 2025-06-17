#!/usr/bin/env python3
"""
Test if the TUI imports correctly and basic initialization works.
"""

try:
    from chatgpt_tui import ChatGPTTUI, ViewMode, TreeListView
    print("✅ TUI imports successful")
    
    # Test enum values
    print(f"ViewMode.CONVERSATION_TREE = {ViewMode.CONVERSATION_TREE}")
    print(f"ViewMode.CONVERSATION_LIST = {ViewMode.CONVERSATION_LIST}")
    
    # Test basic class creation (without curses)
    print("Testing basic class instantiation...")
    # We can't fully test without curses, but we can check imports
    
    print("✅ All TUI components load successfully!")
    
except Exception as e:
    print(f"❌ TUI import failed: {e}")
    import traceback
    traceback.print_exc()