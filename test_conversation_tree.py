#!/usr/bin/env python3
"""
Comprehensive tests for conversation tree functionality.
"""

import unittest
import tempfile
import json
import os
from pathlib import Path
from conversation_tree import (
    TreeManager, MetadataStore, ConversationOrganizer,
    TreeNode, NodeType, ConversationMetadata, OrganizationData
)
from chatgpt_browser import Conversation, Message, MessageRole


class TestTreeManager(unittest.TestCase):
    """Test TreeManager functionality."""
    
    def setUp(self):
        self.tree_manager = TreeManager(debug=True)
    
    def test_create_folder(self):
        """Test folder creation."""
        folder_id = self.tree_manager.create_folder("Test Folder")
        self.assertIsInstance(folder_id, str)
        self.assertIn(folder_id, self.tree_manager.organization_data.tree_nodes)
        
        node = self.tree_manager.organization_data.tree_nodes[folder_id]
        self.assertEqual(node.name, "Test Folder")
        self.assertEqual(node.node_type, NodeType.FOLDER)
        self.assertEqual(node.path, "/Test Folder/")
    
    def test_create_nested_folder(self):
        """Test nested folder creation."""
        parent_id = self.tree_manager.create_folder("Parent")
        child_id = self.tree_manager.create_folder("Child", parent_id)
        
        parent_node = self.tree_manager.organization_data.tree_nodes[parent_id]
        child_node = self.tree_manager.organization_data.tree_nodes[child_id]
        
        self.assertEqual(child_node.parent_id, parent_id)
        self.assertIn(child_id, parent_node.children)
        self.assertEqual(child_node.path, "/Parent/Child/")
    
    def test_add_conversation(self):
        """Test adding conversation to tree."""
        folder_id = self.tree_manager.create_folder("Conversations")
        self.tree_manager.add_conversation("conv-1", folder_id, "Test Conversation")
        
        self.assertIn("conv-1", self.tree_manager.organization_data.tree_nodes)
        conv_node = self.tree_manager.organization_data.tree_nodes["conv-1"]
        
        self.assertEqual(conv_node.node_type, NodeType.CONVERSATION)
        self.assertEqual(conv_node.parent_id, folder_id)
        self.assertEqual(conv_node.name, "Test Conversation")
    
    def test_move_node(self):
        """Test moving nodes between folders."""
        folder1 = self.tree_manager.create_folder("Folder 1")
        folder2 = self.tree_manager.create_folder("Folder 2")
        self.tree_manager.add_conversation("conv-1", folder1)
        
        # Move conversation from folder1 to folder2
        self.tree_manager.move_node("conv-1", folder2)
        
        conv_node = self.tree_manager.organization_data.tree_nodes["conv-1"]
        folder1_node = self.tree_manager.organization_data.tree_nodes[folder1]
        folder2_node = self.tree_manager.organization_data.tree_nodes[folder2]
        
        self.assertEqual(conv_node.parent_id, folder2)
        self.assertNotIn("conv-1", folder1_node.children)
        self.assertIn("conv-1", folder2_node.children)
    
    def test_cycle_detection(self):
        """Test that cycles are prevented."""
        folder1 = self.tree_manager.create_folder("Folder 1")
        folder2 = self.tree_manager.create_folder("Folder 2", folder1)
        
        # Try to move folder1 under folder2 (would create cycle)
        with self.assertRaises(ValueError):
            self.tree_manager.move_node(folder1, folder2)
    
    def test_delete_node(self):
        """Test deleting nodes and descendants."""
        parent = self.tree_manager.create_folder("Parent")
        child = self.tree_manager.create_folder("Child", parent)
        self.tree_manager.add_conversation("conv-1", child)
        
        # Delete parent (should delete child and conversation too)
        self.tree_manager.delete_node(parent)
        
        self.assertNotIn(parent, self.tree_manager.organization_data.tree_nodes)
        self.assertNotIn(child, self.tree_manager.organization_data.tree_nodes)
        self.assertNotIn("conv-1", self.tree_manager.organization_data.tree_nodes)
    
    def test_get_tree_order(self):
        """Test getting nodes in tree order."""
        folder1 = self.tree_manager.create_folder("B Folder")
        folder2 = self.tree_manager.create_folder("A Folder")
        child = self.tree_manager.create_folder("Child", folder1)
        
        tree_order = self.tree_manager.get_tree_order()
        
        # Should be sorted by name, with children after parents
        self.assertEqual(len(tree_order), 3)
        self.assertEqual(tree_order[0].name, "A Folder")
        self.assertEqual(tree_order[1].name, "B Folder")
        self.assertEqual(tree_order[2].name, "Child")


class TestMetadataStore(unittest.TestCase):
    """Test MetadataStore functionality."""
    
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        self.store = MetadataStore(self.temp_file.name, debug=True)
    
    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
        backup_path = Path(self.temp_file.name).with_suffix('.bak')
        if backup_path.exists():
            os.unlink(backup_path)
    
    def test_save_and_load(self):
        """Test saving and loading organization data."""
        # Create test data
        data = OrganizationData()
        folder_node = TreeNode(
            id="folder-1",
            name="Test Folder",
            node_type=NodeType.FOLDER,
            path="/Test Folder/"
        )
        data.tree_nodes["folder-1"] = folder_node
        data.root_nodes.add("folder-1")
        
        # Save and reload
        self.store.save(data)
        loaded_data = self.store.load()
        
        self.assertEqual(len(loaded_data.tree_nodes), 1)
        self.assertIn("folder-1", loaded_data.tree_nodes)
        loaded_node = loaded_data.tree_nodes["folder-1"]
        self.assertEqual(loaded_node.name, "Test Folder")
        self.assertEqual(loaded_node.node_type, NodeType.FOLDER)
    
    def test_load_nonexistent_file(self):
        """Test loading from non-existent file."""
        os.unlink(self.temp_file.name)  # Remove the file
        data = self.store.load()
        
        self.assertIsInstance(data, OrganizationData)
        self.assertEqual(len(data.tree_nodes), 0)


class TestConversationOrganizer(unittest.TestCase):
    """Test ConversationOrganizer functionality."""
    
    def setUp(self):
        # Create temporary conversations file
        self.conversations = [
            Conversation(
                id="conv-1",
                title="Test Conversation 1",
                messages=[
                    Message(id="msg-1", role=MessageRole.USER, content="Hello"),
                    Message(id="msg-2", role=MessageRole.ASSISTANT, content="Hi there!")
                ]
            ),
            Conversation(
                id="conv-2",
                title="Test Conversation 2", 
                messages=[
                    Message(id="msg-3", role=MessageRole.USER, content="How are you?"),
                    Message(id="msg-4", role=MessageRole.ASSISTANT, content="I'm doing well!")
                ]
            )
        ]
        
        # Create temp file with conversation data
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        conv_data = []
        for conv in self.conversations:
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
        
        json.dump(conv_data, self.temp_file)
        self.temp_file.close()
        
        self.organizer = ConversationOrganizer(self.temp_file.name, debug=True)
    
    def tearDown(self):
        os.unlink(self.temp_file.name)
        if self.organizer.organization_path.exists():
            os.unlink(self.organizer.organization_path)
    
    def test_create_folder_and_organize(self):
        """Test creating folders and organizing conversations."""
        folder_id = self.organizer.create_folder("Test Folder")
        self.organizer.add_conversation("conv-1", folder_id)
        
        organized = self.organizer.get_organized_conversations(self.conversations)
        
        # Should have folder and conversation
        self.assertEqual(len(organized), 2)
        folder_item = organized[0]
        conv_item = organized[1]
        
        self.assertIsNone(folder_item[1])  # Folder has no conversation
        self.assertEqual(folder_item[0].name, "Test Folder")
        
        self.assertIsNotNone(conv_item[1])  # Conversation item
        self.assertEqual(conv_item[1].id, "conv-1")
    
    def test_save_and_load_organization(self):
        """Test saving and loading organization."""
        folder_id = self.organizer.create_folder("Saved Folder")
        self.organizer.add_conversation("conv-1", folder_id)
        self.organizer.save_organization()
        
        # Create new organizer to test loading
        new_organizer = ConversationOrganizer(self.temp_file.name, debug=True)
        organized = new_organizer.get_organized_conversations(self.conversations)
        
        # Should load the same organization
        self.assertEqual(len(organized), 2)
        self.assertEqual(organized[0][0].name, "Saved Folder")


if __name__ == "__main__":
    print("🧪 Running conversation tree tests...")
    unittest.main(verbosity=2)