#!/usr/bin/env python3
"""
Simple test script for the conversation tree functionality.
"""

from conversation_tree import ConversationOrganizer, TreeManager, NodeType
from chatgpt_browser import Conversation, MessageRole, Message

# Create some test conversations
test_conversations = [
    Conversation(
        id="conv1",
        title="Python Tutorial",
        messages=[
            Message(id="msg1", role=MessageRole.USER, content="How do I use Python?"),
            Message(id="msg2", role=MessageRole.ASSISTANT, content="Python is a programming language...")
        ]
    ),
    Conversation(
        id="conv2", 
        title="JavaScript Basics",
        messages=[
            Message(id="msg3", role=MessageRole.USER, content="Explain JavaScript"),
            Message(id="msg4", role=MessageRole.ASSISTANT, content="JavaScript is...")
        ]
    ),
    Conversation(
        id="conv3",
        title="Docker Setup",
        messages=[
            Message(id="msg5", role=MessageRole.USER, content="How to use Docker?"),
            Message(id="msg6", role=MessageRole.ASSISTANT, content="Docker is a containerization...")
        ]
    )
]

def test_tree_manager():
    """Test the TreeManager functionality."""
    print("Testing TreeManager...")
    
    tree_manager = TreeManager(debug=True)
    
    # Create some folders
    work_folder = tree_manager.create_folder("Work")
    programming_folder = tree_manager.create_folder("Programming", work_folder)
    devops_folder = tree_manager.create_folder("DevOps", work_folder)
    
    print(f"Created folders: work={work_folder}, programming={programming_folder}, devops={devops_folder}")
    
    # Add conversations to folders
    tree_manager.add_conversation("conv1", programming_folder, "Python Tutorial")
    tree_manager.add_conversation("conv2", programming_folder, "JavaScript Basics")
    tree_manager.add_conversation("conv3", devops_folder, "Docker Setup")
    
    # Get tree order
    tree_order = tree_manager.get_tree_order()
    print("\nTree structure:")
    for node in tree_order:
        depth = node.path.count('/') - 1
        indent = "  " * depth
        node_type = "📁" if node.node_type == NodeType.FOLDER else "💬"
        print(f"{indent}{node_type} {node.name} ({node.path})")
    
    return tree_manager

def test_organizer():
    """Test the ConversationOrganizer functionality."""
    print("\n\nTesting ConversationOrganizer...")
    
    # Create a temporary conversations file for testing
    import json
    import tempfile
    
    conv_data = []
    for conv in test_conversations:
        conv_data.append({
            'id': conv.id,
            'title': conv.title,
            'messages': [
                {
                    'id': msg.id,
                    'role': msg.role.value,
                    'content': msg.content,
                    'create_time': msg.create_time,
                    'author': msg.author
                }
                for msg in conv.messages
            ],
            'create_time': conv.create_time,
            'update_time': conv.update_time
        })
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(conv_data, f)
        temp_path = f.name
    
    try:
        # Create organizer
        organizer = ConversationOrganizer(temp_path, debug=True)
        
        # Create folder structure
        work_folder = organizer.create_folder("Work Projects")
        programming_folder = organizer.create_folder("Programming", work_folder)
        
        # Add conversations
        organizer.add_conversation("conv1", programming_folder)
        organizer.add_conversation("conv2", programming_folder)
        organizer.add_conversation("conv3")  # Root level
        
        # Save organization
        organizer.save_organization()
        print(f"Organization saved to: {organizer.organization_path}")
        
        # Get organized conversations
        organized = organizer.get_organized_conversations(test_conversations)
        print("\nOrganized conversations:")
        for node, conversation in organized:
            depth = node.path.count('/') - 1
            indent = "  " * depth
            node_type = "📁" if node.node_type == NodeType.FOLDER else "💬"
            name = conversation.title if conversation else node.name
            print(f"{indent}{node_type} {name}")
        
        return organizer
        
    finally:
        import os
        os.unlink(temp_path)

if __name__ == "__main__":
    try:
        tree_manager = test_tree_manager()
        organizer = test_organizer()
        print("\n✅ All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()