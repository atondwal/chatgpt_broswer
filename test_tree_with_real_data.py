#!/usr/bin/env python3
"""
Test tree organization with real conversation data.
"""

from pathlib import Path
from conversation_tree import ConversationOrganizer
from chatgpt_browser import ConversationLoader

def main():
    # Use the real conversations file
    conversations_path = Path.home() / '.chatgpt' / 'conversations.json'
    
    if not conversations_path.exists():
        print(f"❌ No conversations file found at {conversations_path}")
        return
    
    print(f"📂 Loading conversations from {conversations_path}")
    
    # Load conversations
    loader = ConversationLoader(debug=True)
    conversations = loader.load_conversations(conversations_path)
    print(f"✅ Loaded {len(conversations)} conversations")
    
    # Create organizer
    organizer = ConversationOrganizer(conversations_path, debug=True)
    
    # Create some example folders
    print("\n📁 Creating folder structure...")
    work_folder = organizer.create_folder("Work Projects")
    learning_folder = organizer.create_folder("Learning")
    coding_folder = organizer.create_folder("Programming", learning_folder)
    ai_folder = organizer.create_folder("AI & ML", learning_folder)
    
    print(f"Created folders: Work={work_folder}, Learning={learning_folder}, Programming={coding_folder}, AI={ai_folder}")
    
    # Add some conversations to folders (first few)
    if len(conversations) >= 3:
        organizer.add_conversation(conversations[0].id, coding_folder)
        organizer.add_conversation(conversations[1].id, ai_folder) 
        organizer.add_conversation(conversations[2].id, work_folder)
        print("✅ Added 3 conversations to folders")
    
    # Save the organization
    organizer.save_organization()
    print(f"💾 Organization saved to: {organizer.organization_path}")
    
    # Test getting organized conversations
    organized = organizer.get_organized_conversations(conversations[:10])  # Just first 10 for testing
    
    print("\n🌳 Tree structure:")
    for node, conversation in organized:
        depth = node.path.count('/') - 1
        indent = "  " * depth
        node_type = "📁" if conversation is None else "💬"
        name = conversation.title if conversation else node.name
        print(f"{indent}{node_type} {name}")
    
    print(f"\n✅ Test completed! Organization file: {organizer.organization_path}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()