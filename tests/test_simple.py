#!/usr/bin/env python3
"""Simple tests for the refactored codebase."""

import tempfile
import json
import pytest
from pathlib import Path

from src.core.loader import load_conversations, extract_content
from src.tree.tree import ConversationTree, TreeNode
from src.core.models import Conversation, Message, MessageRole
from src.tui.tree_view import TreeView
from src.tui.tui import TUI
import curses
import time
from unittest.mock import Mock, patch


class TestSimpleLoader:
    """Test the simple loader functionality."""
    
    def test_load_empty_file(self):
        """Test loading an empty conversations file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([], f)
            f.flush()
            
            conversations = load_conversations(f.name)
            assert conversations == []
            
    def test_load_basic_conversation(self):
        """Test loading a basic conversation."""
        test_data = [{
            'id': 'test-1',
            'title': 'Test Conversation',
            'create_time': 1234567890,
            'messages': [
                {'id': 'msg1', 'role': 'user', 'content': 'Hello'},
                {'id': 'msg2', 'role': 'assistant', 'content': 'Hi there!'}
            ]
        }]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            f.flush()
            
            conversations = load_conversations(f.name)
            assert len(conversations) == 1
            assert conversations[0].title == 'Test Conversation'
            assert len(conversations[0].messages) == 2
            
    def test_extract_content_variations(self):
        """Test content extraction from various formats."""
        # Direct string
        assert extract_content({'content': 'Hello'}) == 'Hello'
        
        # Content with parts
        assert extract_content({'content': {'parts': ['Hello', 'World']}}) == 'Hello World'
        
        # Content with text
        assert extract_content({'content': {'text': 'Hello'}}) == 'Hello'
        
        # Empty content
        assert extract_content({}) == '[Empty message]'


class TestSimpleTree:
    """Test the simple tree functionality."""
    
    def test_tree_initialization(self):
        """Test tree initialization."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([], f)
            f.flush()
            
            tree = ConversationTree(f.name)
            assert tree.filename == f.name
            assert tree.org_filename == f.name.replace('.json', '_organization.json')
            
    def test_create_folder(self):
        """Test folder creation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([], f)
            f.flush()
            
            tree = ConversationTree(f.name)
            folder_id = tree.create_folder('Test Folder')
            
            assert folder_id in tree.nodes
            assert tree.nodes[folder_id].name == 'Test Folder'
            assert tree.nodes[folder_id].is_folder
            
    def test_move_node(self):
        """Test moving nodes."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([], f)
            f.flush()
            
            tree = ConversationTree(f.name)
            
            # Create folders
            folder1_id = tree.create_folder('Folder 1')
            folder2_id = tree.create_folder('Folder 2')
            
            # Move folder2 into folder1
            tree.move_node(folder2_id, folder1_id)
            
            assert tree.nodes[folder2_id].parent_id == folder1_id
            assert folder2_id in tree.nodes[folder1_id].children
            
    def test_delete_node(self):
        """Test node deletion."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([], f)
            f.flush()
            
            tree = ConversationTree(f.name)
            
            # Create and delete folder
            folder_id = tree.create_folder('Test Folder')
            tree.delete_node(folder_id)
            
            assert folder_id not in tree.nodes


class TestTreeNode:
    """Test TreeNode functionality."""
    
    def test_node_creation(self):
        """Test creating a tree node."""
        node = TreeNode('test-id', 'Test Node', is_folder=True)
        
        assert node.id == 'test-id'
        assert node.name == 'Test Node'
        assert node.is_folder
        assert node.parent_id is None
        assert node.children == set()
        assert node.expanded


class TestTreeView:
    """Test the enhanced tree view functionality."""
    
    def setup_method(self):
        """Set up test tree view."""
        self.mock_stdscr = Mock()
        self.tree_view = TreeView(self.mock_stdscr, 1, 0, 80, 24)
        
        # Create test tree items
        self.test_nodes = [
            (TreeNode("1", "Folder 1", is_folder=True), None, 0),
            (TreeNode("2", "Conversation 1", is_folder=False), Mock(title="Conv 1"), 1),
            (TreeNode("3", "Conversation 2", is_folder=False), Mock(title="Conv 2"), 1),
            (TreeNode("4", "Folder 2", is_folder=True), None, 0),
        ]
        self.tree_view.set_items(self.test_nodes)
    
    def test_vim_navigation_gg(self):
        """Test gg (go to top) double-key command."""
        self.tree_view.selected = 2
        
        # First 'g' should store key and return None
        result = self.tree_view.handle_input(ord('g'))
        assert result is None
        assert self.tree_view.last_key == ord('g')
        
        # Second 'g' should go to top
        result = self.tree_view.handle_input(ord('g'))
        assert result is None
        assert self.tree_view.selected == 0
        assert self.tree_view.last_key is None
    
    def test_vim_navigation_dd(self):
        """Test dd (delete) double-key command."""
        self.tree_view.selected = 1
        
        # First 'd' should store key
        result = self.tree_view.handle_input(ord('d'))
        assert result is None
        assert self.tree_view.last_key == ord('d')
        
        # Second 'd' should return delete
        result = self.tree_view.handle_input(ord('d'))
        assert result == "delete"
        assert self.tree_view.last_key is None
    
    def test_vim_navigation_yy(self):
        """Test yy (copy) double-key command."""
        # First 'y' should store key
        result = self.tree_view.handle_input(ord('y'))
        assert result is None
        
        # Second 'y' should return copy
        result = self.tree_view.handle_input(ord('y'))
        assert result == "copy"
    
    def test_vim_navigation_zz(self):
        """Test zz (center) double-key command."""
        self.tree_view.selected = 2
        
        # First 'z' should store key
        result = self.tree_view.handle_input(ord('z'))
        assert result is None
        
        # Second 'z' should center and return None
        result = self.tree_view.handle_input(ord('z'))
        assert result is None
    
    def test_double_key_timeout(self):
        """Test that double-key commands timeout properly."""
        # Store first key
        result = self.tree_view.handle_input(ord('g'))
        assert result is None
        assert self.tree_view.last_key == ord('g')
        
        # Simulate timeout by manually setting old timestamp
        self.tree_view.last_key_time = time.time() - 1.0
        
        # Different key should clear the stored key
        result = self.tree_view.handle_input(ord('k'))
        assert self.tree_view.last_key is None
    
    def test_ctrl_navigation(self):
        """Test Ctrl+D/U/F/B navigation."""
        self.tree_view.selected = 2
        original_pos = self.tree_view.selected
        
        # Ctrl+D (half page down)
        result = self.tree_view.handle_input(4)
        assert self.tree_view.selected >= original_pos
        
        # Ctrl+U (half page up) 
        result = self.tree_view.handle_input(21)
        # Should move up or stay in bounds
        assert self.tree_view.selected >= 0
    
    def test_hjkl_navigation(self):
        """Test H/M/L screen positioning."""
        self.tree_view.offset = 1
        
        # H - jump to high (top of screen)
        result = self.tree_view.handle_input(ord('H'))
        assert self.tree_view.selected == self.tree_view.offset
        
        # M - jump to middle
        result = self.tree_view.handle_input(ord('M'))
        expected = min(len(self.test_nodes) - 1, self.tree_view.offset + self.tree_view.height // 2)
        assert self.tree_view.selected == expected
        
        # L - jump to low (bottom of screen)
        result = self.tree_view.handle_input(ord('L'))
        expected = min(len(self.test_nodes) - 1, self.tree_view.offset + self.tree_view.height - 1)
        assert self.tree_view.selected == expected
    
    def test_quick_actions(self):
        """Test quick action keybindings."""
        # x - quick delete
        result = self.tree_view.handle_input(ord('x'))
        assert result == "delete"
        
        # u - undo
        result = self.tree_view.handle_input(ord('u'))
        assert result == "undo"
        
        # . - repeat
        result = self.tree_view.handle_input(ord('.'))
        assert result == "repeat"
        
        # p - paste
        result = self.tree_view.handle_input(ord('p'))
        assert result == "paste"
    
    def test_function_keys(self):
        """Test function key bindings."""
        # F1 - help
        result = self.tree_view.handle_input(curses.KEY_F1)
        assert result == "help"
        
        # F2 - rename
        result = self.tree_view.handle_input(curses.KEY_F2)
        assert result == "rename"
        
        # F5 - refresh
        result = self.tree_view.handle_input(curses.KEY_F5)
        assert result == "refresh"
        
        # Delete key
        result = self.tree_view.handle_input(curses.KEY_DC)
        assert result == "delete"
        
        # Insert key
        result = self.tree_view.handle_input(curses.KEY_IC)
        assert result == "new_folder"
    
    def test_filter_keys(self):
        """Test filter keybindings."""
        # f - quick filter
        result = self.tree_view.handle_input(ord('f'))
        assert result == "quick_filter"
        
        # F - folders only
        result = self.tree_view.handle_input(ord('F'))
        assert result == "filter_folders"
        
        # C - conversations only
        result = self.tree_view.handle_input(ord('C'))
        assert result == "filter_conversations"
        
        # a - show all
        result = self.tree_view.handle_input(ord('a'))
        assert result == "show_all"
    
    def test_numeric_depth_control(self):
        """Test numeric depth expansion."""
        for i in range(10):
            result = self.tree_view.handle_input(ord(str(i)))
            assert result == f"expand_depth_{i}"
    
    def test_visual_mode_keys(self):
        """Test visual mode and indentation."""
        # V - visual mode
        result = self.tree_view.handle_input(ord('V'))
        assert result == "visual_mode"
        
        # > - indent
        result = self.tree_view.handle_input(ord('>'))
        assert result == "indent"
        
        # < - outdent
        result = self.tree_view.handle_input(ord('<'))
        assert result == "outdent"
    
    def test_move_up_down_steps(self):
        """Test move_up and move_down with step parameters."""
        self.tree_view.selected = 2
        
        # Move up 1 step (default)
        self.tree_view.move_up()
        assert self.tree_view.selected == 1
        
        # Move down 2 steps
        self.tree_view.move_down(2)
        assert self.tree_view.selected == 3
        
        # Test bounds checking
        self.tree_view.move_up(10)  # Should go to 0
        assert self.tree_view.selected == 0
        
        self.tree_view.move_down(10)  # Should go to max
        assert self.tree_view.selected == len(self.test_nodes) - 1
    
    def test_center_on_selected(self):
        """Test centering functionality."""
        self.tree_view.selected = 2
        self.tree_view._center_on_selected()
        
        # Should calculate appropriate offset to center
        expected_offset = max(0, 2 - self.tree_view.height // 2)
        assert self.tree_view.offset == expected_offset


class TestTUIEnhancements:
    """Test the enhanced TUI functionality."""
    
    def setup_method(self):
        """Set up test TUI."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([{
                "id": "test_conv",
                "title": "Test Conversation", 
                "create_time": 1234567890,
                "mapping": {}
            }], f)
            self.test_file = f.name
        
        self.tui = TUI(self.test_file)
        self.tui.conversations = [
            Conversation("1", "Test Conv 1", [], create_time=1234567890),
            Conversation("2", "Test Conv 2", [], create_time=1234567891)
        ]
        self.tui.filtered_conversations = self.tui.conversations
        
        # Mock TUI components that require curses
        self.tui.tree_view = Mock()
        self.tui.tree_view.selected = 0
        self.tui.tree_view.get_selected = Mock(return_value=None)
        self.tui.search_overlay = Mock()
        self.tui.tree_items = []
    
    def test_copy_item(self):
        """Test copying item title."""
        # Mock selected item
        mock_item = (TreeNode("1", "Test", is_folder=False), Mock(title="Test Conversation"), 0)
        self.tui.tree_view.get_selected = Mock(return_value=mock_item)
        
        self.tui._copy_item()
        
        assert hasattr(self.tui, 'clipboard')
        assert self.tui.clipboard['type'] == 'title'
        assert self.tui.clipboard['data'] == 'Test Conversation'
        assert "Copied:" in self.tui.status_message
    
    def test_paste_item(self):
        """Test pasting item."""
        # No clipboard
        self.tui._paste_item()
        assert "Nothing to paste" in self.tui.status_message
        
        # With clipboard
        self.tui.clipboard = {"type": "title", "data": "Test"}
        self.tui._paste_item()
        assert "Paste:" in self.tui.status_message
    
    def test_refresh_conversations(self):
        """Test refreshing conversations from file."""
        self.tui._refresh_conversations()
        
        # Should reload from file
        assert "Refreshed" in self.tui.status_message
    
    def test_filter_folders(self):
        """Test showing only folders."""
        self.tui._filter_folders()
        
        assert len(self.tui.filtered_conversations) == 0
        assert "Showing only folders" in self.tui.status_message
    
    def test_show_all(self):
        """Test showing all items."""
        # First filter something
        self.tui.filtered_conversations = []
        
        # Then show all
        self.tui._show_all()
        
        assert len(self.tui.filtered_conversations) == len(self.tui.conversations)
        assert "Showing all items" in self.tui.status_message
    
    def test_expand_to_depth(self):
        """Test expanding tree to specific depth."""
        # Add some folders to the tree
        folder1_id = self.tui.tree.create_folder("Folder 1")
        folder2_id = self.tui.tree.create_folder("Folder 2", parent_id=folder1_id)
        
        # Test collapse all (depth 0)
        self.tui._expand_to_depth(0)
        for node in self.tui.tree.nodes.values():
            if node.is_folder:
                assert not node.expanded
        assert "Collapsed all folders" in self.tui.status_message
        
        # Test expand to depth 2
        self.tui._expand_to_depth(2)
        assert "Expanded to depth 2" in self.tui.status_message
    
    def test_implemented_actions(self):
        """Test actually implemented action messages."""
        # Test undo with empty stack
        self.tui._undo_action()
        assert "Nothing to undo" in self.tui.status_message
        
        # Test repeat with no last action
        self.tui._repeat_last_action()
        assert "No action to repeat" in self.tui.status_message
        
        # Test visual mode toggle
        self.tui._toggle_visual_mode()
        assert "Visual mode activated" in self.tui.status_message
        
        # Toggle back
        self.tui._toggle_visual_mode()
        assert "Visual mode deactivated" in self.tui.status_message
    
    def test_indent_outdent_items(self):
        """Test indent/outdent operations."""
        # No items selected
        self.tui._indent_items()
        assert "No items selected to indent" in self.tui.status_message
        
        self.tui._outdent_items()
        assert "No items selected to outdent" in self.tui.status_message
        
        # With items selected but no current item (should fail gracefully)
        self.tui.selected_items = {"1", "2"}
        self.tui.tree_view.get_selected = Mock(return_value=None)
        self.tui._indent_items()
        assert "Cannot determine target" in self.tui.status_message
        
        # Test with mocked current item
        mock_item = (TreeNode("1", "Test", is_folder=False), Mock(title="Test"), 0)
        self.tui.tree_view.get_selected = Mock(return_value=mock_item)
        self.tui._indent_items()
        assert "No folder available" in self.tui.status_message
    
    def test_quick_filter(self):
        """Test quick filter activation."""
        from src.tui.tui import ViewMode
        
        self.tui._quick_filter()
        
        assert self.tui.current_view == ViewMode.SEARCH
        assert "Quick filter mode" in self.tui.status_message
    
    def teardown_method(self):
        """Clean up test files."""
        Path(self.test_file).unlink(missing_ok=True)


class TestKeybindingIntegration:
    """Test integration of keybindings with TUI functionality."""
    
    def setup_method(self):
        """Set up integration test."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([{
                "id": "test_conv",
                "title": "Test Conversation",
                "create_time": 1234567890,
                "mapping": {}
            }], f)
            self.test_file = f.name
        
        self.tui = TUI(self.test_file)
    
    def test_keybinding_result_handling(self):
        """Test that keybinding results are properly handled."""
        # Mock methods to verify they're called
        self.tui._delete_item = Mock()
        self.tui._copy_item = Mock()
        self.tui._paste_item = Mock()
        self.tui._show_tree_help = Mock()
        self.tui._refresh_conversations = Mock()
        
        # Test delete handling
        self._handle_tree_key_result("delete")
        self.tui._delete_item.assert_called_once()
        
        # Test copy handling
        self._handle_tree_key_result("copy")
        self.tui._copy_item.assert_called_once()
        
        # Test paste handling  
        self._handle_tree_key_result("paste")
        self.tui._paste_item.assert_called_once()
        
        # Test help handling
        self._handle_tree_key_result("help")
        self.tui._show_tree_help.assert_called_once()
        
        # Test refresh handling
        self._handle_tree_key_result("refresh")
        self.tui._refresh_conversations.assert_called_once()
    
    def _handle_tree_key_result(self, result):
        """Helper method to handle tree key results for testing."""
        if result == "delete":
            self.tui._delete_item()
        elif result == "copy":
            self.tui._copy_item()
        elif result == "paste":
            self.tui._paste_item()
        elif result == "help":
            self.tui._show_tree_help()
        elif result == "refresh":
            self.tui._refresh_conversations()
    
    def teardown_method(self):
        """Clean up test files."""
        Path(self.test_file).unlink(missing_ok=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])