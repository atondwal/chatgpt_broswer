#!/usr/bin/env python3
"""
Demo script to create a comprehensive folder structure and test tree functionality.
"""

from pathlib import Path
from conversation_tree import ConversationOrganizer
from chatgpt_browser import ConversationLoader

def main():
    """Create a comprehensive demo organization structure."""
    conversations_path = Path.home() / '.chatgpt' / 'conversations.json'
    
    if not conversations_path.exists():
        print(f"❌ No conversations file found at {conversations_path}")
        return
    
    print(f"📂 Loading conversations from {conversations_path}")
    
    # Load conversations
    loader = ConversationLoader()
    conversations = loader.load_conversations(conversations_path)
    print(f"✅ Loaded {len(conversations)} conversations")
    
    # Create organizer
    organizer = ConversationOrganizer(conversations_path, debug=True)
    
    # Clear any existing organization to start fresh
    organizer.tree_manager.organization_data.tree_nodes.clear()
    organizer.tree_manager.organization_data.root_nodes.clear()
    organizer.tree_manager.organization_data.conversation_metadata.clear()
    
    print("\n📁 Creating comprehensive folder structure...")
    
    # Create main categories
    work_folder = organizer.create_folder("💼 Work Projects")
    learning_folder = organizer.create_folder("📚 Learning & Education")
    personal_folder = organizer.create_folder("🏠 Personal")
    archive_folder = organizer.create_folder("📦 Archive")
    
    # Work subfolders
    coding_work = organizer.create_folder("💻 Software Development", work_folder)
    meetings = organizer.create_folder("🤝 Meetings & Planning", work_folder)
    documentation = organizer.create_folder("📄 Documentation", work_folder)
    
    # Learning subfolders
    programming = organizer.create_folder("👨‍💻 Programming", learning_folder)
    ai_ml = organizer.create_folder("🤖 AI & Machine Learning", learning_folder)
    math_science = organizer.create_folder("🧮 Math & Science", learning_folder)
    
    # Programming sub-subfolders
    python_folder = organizer.create_folder("🐍 Python", programming)
    javascript_folder = organizer.create_folder("🟨 JavaScript", programming)
    web_dev = organizer.create_folder("🌐 Web Development", programming)
    
    # AI/ML subfolders
    deep_learning = organizer.create_folder("🧠 Deep Learning", ai_ml)
    nlp_folder = organizer.create_folder("💬 NLP", ai_ml)
    computer_vision = organizer.create_folder("👁️ Computer Vision", ai_ml)
    
    # Personal subfolders
    creative = organizer.create_folder("🎨 Creative Projects", personal_folder)
    health_fitness = organizer.create_folder("💪 Health & Fitness", personal_folder)
    travel = organizer.create_folder("✈️ Travel", personal_folder)
    
    print("✅ Created comprehensive folder structure")
    
    # Distribute conversations across folders
    print("\n📊 Organizing conversations into folders...")
    
    # Get some conversations to organize
    sample_convs = conversations[:20] if len(conversations) >= 20 else conversations
    
    folder_assignments = [
        (python_folder, "Programming", ["python", "script", "code", "function", "class"]),
        (javascript_folder, "JavaScript", ["javascript", "js", "react", "node", "npm"]),
        (web_dev, "Web Dev", ["html", "css", "frontend", "backend", "api", "server"]),
        (ai_ml, "AI/ML", ["ai", "machine learning", "neural", "model", "training"]),
        (deep_learning, "Deep Learning", ["tensorflow", "pytorch", "cnn", "rnn", "transformer"]),
        (nlp_folder, "NLP", ["nlp", "language", "text", "chatgpt", "conversation"]),
        (work_folder, "Work", ["project", "meeting", "team", "deadline", "client"]),
        (creative, "Creative", ["design", "art", "creative", "writing", "story"]),
        (archive_folder, "Archive", ["old", "deprecated", "backup", "archive"])
    ]
    
    organized_count = 0
    for i, conv in enumerate(sample_convs):
        # Simple keyword-based assignment
        title_lower = conv.title.lower()
        assigned = False
        
        for folder_id, folder_name, keywords in folder_assignments:
            if any(keyword in title_lower for keyword in keywords):
                organizer.add_conversation(conv.id, folder_id)
                print(f"  📋 '{conv.title}' → {folder_name}")
                organized_count += 1
                assigned = True
                break
        
        if not assigned and i < 5:  # Put first few unassigned at root level
            organizer.add_conversation(conv.id)
            print(f"  📋 '{conv.title}' → Root level")
            organized_count += 1
    
    print(f"✅ Organized {organized_count} conversations")
    
    # Update some conversation metadata
    if organized_count > 0:
        print("\n🏷️ Adding metadata to conversations...")
        first_conv = sample_convs[0]
        organizer.update_conversation_metadata(
            first_conv.id,
            custom_title=f"⭐ {first_conv.title}",
            tags={"important", "featured", "demo"},
            notes="This is a demo conversation with custom metadata",
            favorite=True
        )
        print(f"  ⭐ Added metadata to '{first_conv.title}'")
    
    # Save the organization
    organizer.save_organization()
    print(f"\n💾 Organization saved to: {organizer.organization_path}")
    
    # Display the tree structure
    organized = organizer.get_organized_conversations(conversations[:30])
    
    print(f"\n🌳 Tree structure preview (showing first 30 conversations):")
    print("=" * 60)
    
    for node, conversation in organized:
        depth = node.path.count('/') - 1
        indent = "  " * depth
        
        if conversation is None:  # Folder
            node_type = "📁"
            name = node.name
            count = f" ({len(node.children)})" if node.children else ""
            expanded = " ▼" if node.expanded else " ▶"
        else:  # Conversation
            node_type = "💬"
            name = conversation.title
            count = f" ({conversation.message_count})"
            expanded = ""
        
        print(f"{indent}{node_type}{expanded} {name}{count}")
    
    print("=" * 60)
    print(f"\n🎉 Demo organization completed!")
    print(f"📁 Total folders: {len([n for n in organizer.tree_manager.organization_data.tree_nodes.values() if n.node_type.name == 'FOLDER'])}")
    print(f"💬 Total organized conversations: {len([n for n in organizer.tree_manager.organization_data.tree_nodes.values() if n.node_type.name == 'CONVERSATION'])}")
    print(f"\n🖥️  Now try: python chatgpt_browser.py tui")
    print(f"   Press 't' to switch to tree view!")
    print(f"   Press 'l' to switch back to list view!")
    print(f"   Use arrow keys and spacebar to navigate!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()