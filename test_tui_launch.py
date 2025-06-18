#!/usr/bin/env python3
"""
Test TUI launch without actually running the full interface.
"""

import sys
import tempfile
import json
from pathlib import Path

def test_tui_initialization():
    """Test that TUI can be initialized without errors."""
    print("🧪 Testing TUI initialization...")
    
    try:
        from chatgpt_tui import ChatGPTTUI, ViewMode, TreeListView
        from conversation_tree import ConversationOrganizer
        
        # Test basic class creation
        tui = ChatGPTTUI(debug=True)
        print("✅ ChatGPTTUI instance created successfully")
        
        # Test that we can access the new view mode
        tree_mode = ViewMode.CONVERSATION_TREE
        print(f"✅ CONVERSATION_TREE mode available: {tree_mode}")
        
        # Test that organizer can be created
        conversations_path = Path.home() / '.chatgpt' / 'conversations.json'
        if conversations_path.exists():
            organizer = ConversationOrganizer(conversations_path, debug=True)
            print("✅ ConversationOrganizer created successfully")
            
            # Test that we can get organized conversations
            from chatgpt_browser import ConversationLoader
            loader = ConversationLoader()
            conversations = loader.load_conversations(conversations_path)
            
            organized = organizer.get_organized_conversations(conversations[:5])
            print(f"✅ Got {len(organized)} organized items")
            
        print("✅ All TUI components initialized successfully!")
        
        # Assertions for pytest
        assert tui is not None
        assert tree_mode == ViewMode.CONVERSATION_TREE
        
    except Exception as e:
        print(f"❌ TUI initialization failed: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"TUI initialization failed: {e}"

def test_tree_functionality():
    """Test tree functionality without curses."""
    print("\n🌳 Testing tree functionality...")
    
    try:
        from conversation_tree import TreeManager, ConversationOrganizer
        from chatgpt_browser import Conversation, Message, MessageRole
        
        # Create test conversations
        test_convs = [
            Conversation(
                id="test-1",
                title="Python Testing",
                messages=[Message(id="msg1", role=MessageRole.USER, content="Test")]
            ),
            Conversation(
                id="test-2", 
                title="JavaScript Guide",
                messages=[Message(id="msg2", role=MessageRole.ASSISTANT, content="Response")]
            )
        ]
        
        # Create temporary organizer
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([{
                'id': conv.id,
                'title': conv.title,
                'messages': [{
                    'id': msg.id,
                    'role': msg.role.value,
                    'content': msg.content
                } for msg in conv.messages]
            } for conv in test_convs], f)
            temp_path = f.name
        
        try:
            organizer = ConversationOrganizer(temp_path, debug=True)
            
            # Create test structure
            folder_id = organizer.create_folder("Test Folder")
            organizer.add_conversation("test-1", folder_id)
            organizer.add_conversation("test-2")  # Root level
            
            # Get organized conversations
            organized = organizer.get_organized_conversations(test_convs)
            
            print(f"✅ Created folder and organized {len(organized)} items")
            
            # Verify structure
            has_folder = any(item[1] is None for item in organized)  # Folder
            has_conv = any(item[1] is not None for item in organized)  # Conversation
            
            if has_folder and has_conv:
                print("✅ Tree structure contains both folders and conversations")
            else:
                print("⚠️  Tree structure incomplete")
                
            # Assertions for pytest
            assert len(organized) >= 2
            assert has_folder and has_conv
            
        finally:
            import os
            os.unlink(temp_path)
            
    except Exception as e:
        print(f"❌ Tree functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"Tree functionality test failed: {e}"
        return False

def main():
    """Run all tests."""
    print("🚀 Running TUI Launch Tests")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 2
    
    if test_tui_initialization():
        tests_passed += 1
        
    if test_tree_functionality():
        tests_passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Final Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! TUI should launch successfully.")
        print("\n💡 To test the actual TUI, run:")
        print("   python chatgpt_browser.py tui")
        print("   Then press 't' to switch to tree view!")
    else:
        print("❌ Some tests failed. Check the errors above.")
        
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)