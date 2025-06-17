#!/usr/bin/env python3
"""
Test the TUI tree view functionality without actually launching curses.
"""

from pathlib import Path
from conversation_tree import ConversationOrganizer, NodeType
from chatgpt_browser import ConversationLoader
from chatgpt_tui import TreeListView, WindowDimensions

def test_tree_view_logic():
    """Test the tree view logic without curses."""
    print("🧪 Testing TreeListView logic...")
    
    # Load real conversations
    conversations_path = Path.home() / '.chatgpt' / 'conversations.json'
    if not conversations_path.exists():
        print("❌ No conversations file found")
        return
        
    loader = ConversationLoader()
    conversations = loader.load_conversations(conversations_path)
    
    # Create organizer (should load existing organization)
    organizer = ConversationOrganizer(conversations_path)
    organized = organizer.get_organized_conversations(conversations[:10])
    
    print(f"✅ Loaded {len(conversations)} conversations")
    print(f"✅ Got {len(organized)} organized items")
    
    # Create a mock TreeListView
    mock_dims = WindowDimensions(height=20, width=80)
    
    # We can't create the actual view without stdscr, but we can test the data processing
    print("\n🌳 Organized structure would be:")
    for node, conversation in organized:
        depth = node.path.count('/') - 1
        indent = "  " * depth
        node_type = "📁" if node.node_type == NodeType.FOLDER else "💬"
        
        if conversation:
            name = conversation.title
            msg_count = f" ({conversation.message_count})"
        else:
            name = node.name
            msg_count = f" ({len(node.children)})" if node.children else ""
            
        print(f"{indent}{node_type} {name}{msg_count}")
    
    print("\n✅ TreeListView logic test completed!")

if __name__ == "__main__":
    try:
        test_tree_view_logic()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()