#!/usr/bin/env python3
"""Tests for refactored TUI modules."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from chatgpt_browser.core.models import Conversation, Message, MessageRole
from chatgpt_browser.tree.tree import ConversationTree
from chatgpt_browser.tui.tui_state import UIState, ViewMode, TUIInitializer, ManagerRegistry, validate_tui_environment
from chatgpt_browser.tui.tui_utils import ActionDispatcher, TreeUpdater, create_action_context
from chatgpt_browser.tui.action_handler import ActionResult


class TestUIState:
    """Test UI state management."""
    
    def test_ui_state_creation(self):
        """Test UI state creation with defaults."""
        state = UIState(conversations_file="/test/path")
        
        assert state.conversations_file == "/test/path"
        assert state.debug is False
        assert state.current_view == ViewMode.TREE
        assert state.running is True
        assert state.status_message == ""
        assert state.tree_offset == 0
        assert state.tree_selected == 0
        assert state.sort_by_date is True
        assert state.search_term == ""
        assert len(state.tree_items) == 0
        assert len(state.filtered_conversations) == 0
    
    def test_ui_state_with_custom_values(self):
        """Test UI state creation with custom values."""
        state = UIState(
            conversations_file="/custom/path",
            debug=True,
            current_view=ViewMode.SEARCH,
            running=False,
            status_message="Test message",
            sort_by_date=False
        )
        
        assert state.conversations_file == "/custom/path"
        assert state.debug is True
        assert state.current_view == ViewMode.SEARCH
        assert state.running is False
        assert state.status_message == "Test message"
        assert state.sort_by_date is False


class TestTUIInitializer:
    """Test TUI initialization functionality."""
    
    def setup_method(self):
        """Set up test data."""
        self.test_conversations = [
            Conversation(
                id="conv1",
                title="Test Conversation 1",
                create_time=1234567890,
                update_time=1234567891,
                messages=[
                    Message(id="msg1", role=MessageRole.USER, content="Hello"),
                    Message(id="msg2", role=MessageRole.ASSISTANT, content="Hi there!")
                ]
            )
        ]
    
    def test_initializer_creation(self):
        """Test initializer creation."""
        initializer = TUIInitializer("/test/path", debug=True, format="claude")
        
        assert initializer.conversations_file == "/test/path"
        assert initializer.debug is True
        assert initializer.format == "claude"
    
    @patch('chatgpt_browser.core.loader.load_conversations')
    def test_initialize_data_success(self, mock_load):
        """Test successful data initialization."""
        mock_load.return_value = self.test_conversations
        
        with tempfile.TemporaryDirectory() as tmpdir:
            initializer = TUIInitializer(tmpdir)
            conversations, tree = initializer.initialize_data()
            
            assert conversations == self.test_conversations
            assert isinstance(tree, ConversationTree)
            mock_load.assert_called_once_with(tmpdir, format="auto")
    
    @patch('chatgpt_browser.core.loader.load_conversations')
    def test_initialize_data_failure(self, mock_load):
        """Test data initialization failure."""
        mock_load.side_effect = Exception("Load failed")
        
        initializer = TUIInitializer("/nonexistent")
        
        with pytest.raises(Exception, match="Load failed"):
            initializer.initialize_data()
    
    def test_create_initial_state(self):
        """Test initial state creation."""
        initializer = TUIInitializer("/test/path", debug=True)
        state = initializer.create_initial_state(self.test_conversations)
        
        assert state.conversations_file == "/test/path"
        assert state.debug is True
        assert state.filtered_conversations == self.test_conversations
    
    @patch('curses.start_color')
    @patch('curses.use_default_colors')
    @patch('curses.init_pair')
    def test_setup_colors_success(self, mock_init_pair, mock_use_default, mock_start_color):
        """Test successful color setup."""
        mock_stdscr = Mock()
        initializer = TUIInitializer("/test/path")
        
        initializer.setup_colors(mock_stdscr)
        
        mock_start_color.assert_called_once()
        mock_use_default.assert_called_once()
        assert mock_init_pair.call_count == 3  # Three color pairs
    
    @patch('curses.start_color')
    def test_setup_colors_failure(self, mock_start_color):
        """Test color setup failure handling."""
        import curses
        mock_start_color.side_effect = curses.error("Color not supported")
        
        mock_stdscr = Mock()
        initializer = TUIInitializer("/test/path")
        
        # Should not raise exception
        initializer.setup_colors(mock_stdscr)


class TestManagerRegistry:
    """Test manager registry functionality."""
    
    def test_registry_creation(self):
        """Test manager registry creation."""
        registry = ManagerRegistry()
        assert len(registry.managers) == 0
    
    @patch('chatgpt_browser.tui.selection_manager.SelectionManager')
    @patch('chatgpt_browser.tui.search_manager.SearchManager') 
    @patch('chatgpt_browser.tui.action_manager.ActionManager')
    @patch('chatgpt_browser.tui.fzf_search.FZFSearch')
    @patch('chatgpt_browser.tui.operations_manager.OperationsManager')
    @patch('chatgpt_browser.tui.tree_manager.TreeManager')
    def test_register_managers_success(self, mock_tree_mgr, mock_ops_mgr, mock_fzf, 
                                     mock_action_mgr, mock_search_mgr, mock_sel_mgr):
        """Test successful manager registration."""
        # Setup mocks
        mock_stdscr = Mock()
        mock_state = UIState(conversations_file="/test")
        mock_conversations = []
        mock_tree = Mock()
        
        registry = ManagerRegistry()
        managers = registry.register_managers(mock_stdscr, mock_state, mock_conversations, mock_tree)
        
        assert len(managers) == 6
        assert len(registry.managers) == 6
        
        # Verify all manager types were instantiated
        mock_sel_mgr.assert_called_once()
        mock_search_mgr.assert_called_once()
        mock_action_mgr.assert_called_once()
        mock_fzf.assert_called_once()
        mock_ops_mgr.assert_called_once_with(mock_stdscr, mock_conversations, mock_tree)
        mock_tree_mgr.assert_called_once_with(mock_stdscr, mock_conversations, mock_tree)


class TestActionDispatcher:
    """Test action dispatcher functionality."""
    
    def test_dispatcher_creation(self):
        """Test action dispatcher creation."""
        managers = []
        dispatcher = ActionDispatcher(managers)
        assert dispatcher.managers == managers
    
    def test_dispatch_action_success(self):
        """Test successful action dispatch."""
        mock_manager = Mock()
        mock_manager.can_handle.return_value = True
        mock_manager.handle.return_value = ActionResult(True, message="Success")
        
        dispatcher = ActionDispatcher([mock_manager])
        context = Mock()
        
        result = dispatcher.dispatch_action("test_action", context)
        
        assert result.success is True
        assert result.message == "Success"
        mock_manager.can_handle.assert_called_once_with("test_action")
        mock_manager.handle.assert_called_once_with("test_action", context)
    
    def test_dispatch_action_no_handler(self):
        """Test action dispatch with no handler."""
        mock_manager = Mock()
        mock_manager.can_handle.return_value = False
        
        dispatcher = ActionDispatcher([mock_manager])
        context = Mock()
        
        result = dispatcher.dispatch_action("unknown_action", context)
        
        assert result.success is False
        assert "Unknown action" in result.message
        mock_manager.can_handle.assert_called_once_with("unknown_action")
        mock_manager.handle.assert_not_called()
    
    def test_dispatch_action_handler_error(self):
        """Test action dispatch with handler error."""
        mock_manager = Mock()
        mock_manager.can_handle.return_value = True
        mock_manager.handle.side_effect = Exception("Handler failed")
        
        dispatcher = ActionDispatcher([mock_manager])
        context = Mock()
        
        result = dispatcher.dispatch_action("test_action", context)
        
        assert result.success is False
        assert "Error:" in result.message


class TestTreeUpdater:
    """Test tree updater functionality."""
    
    def setup_method(self):
        """Set up test data."""
        self.conversations = [
            Conversation(
                id="conv1",
                title="Test Conv 1",
                create_time=1234567890,
                update_time=1234567891,
                messages=[]
            ),
            Conversation(
                id="conv2", 
                title="Test Conv 2",
                create_time=1234567892,
                update_time=1234567893,
                messages=[]
            )
        ]
        
        self.tree = Mock()
        self.tree.root_nodes = []
        self.tree.nodes = {}
    
    def test_tree_updater_creation(self):
        """Test tree updater creation."""
        updater = TreeUpdater(self.conversations, self.tree)
        assert updater.conversations == self.conversations
        assert updater.tree == self.tree
    
    def test_refresh_tree_items_empty(self):
        """Test refreshing tree items with empty tree."""
        ui_state = UIState(conversations_file="/test")
        ui_state.filtered_conversations = self.conversations
        
        updater = TreeUpdater(self.conversations, self.tree)
        updater.refresh_tree_items(ui_state)
        
        # Should have items for orphaned conversations
        assert len(ui_state.tree_items) == 2
        assert ui_state.tree_selected == 0
    
    def test_refresh_tree_items_selected_bounds(self):
        """Test tree refresh with selected index out of bounds."""
        ui_state = UIState(conversations_file="/test")
        ui_state.filtered_conversations = []
        ui_state.tree_selected = 10  # Out of bounds
        
        updater = TreeUpdater(self.conversations, self.tree)
        updater.refresh_tree_items(ui_state)
        
        # Should reset selected to 0 when no items
        assert ui_state.tree_selected == 0


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_action_context(self):
        """Test action context creation."""
        mock_tui = Mock()
        
        context = create_action_context(mock_tui, key=65, result="test_result")
        
        assert context.tui == mock_tui
        assert context.key == 65
        assert context.result == "test_result"
    
    @patch('sys.stdout.isatty')
    @patch('os.get_terminal_size')
    @patch('os.environ.get')
    def test_validate_tui_environment_success(self, mock_env_get, mock_term_size, mock_isatty):
        """Test successful TUI environment validation."""
        mock_isatty.return_value = True
        mock_term_size.return_value = os.terminal_size((25, 80))
        mock_env_get.return_value = "xterm"
        
        result = validate_tui_environment()
        assert result is True
    
    @patch('sys.stdout.isatty')
    def test_validate_tui_environment_not_tty(self, mock_isatty):
        """Test TUI environment validation failure - not a TTY."""
        mock_isatty.return_value = False
        
        result = validate_tui_environment()
        assert result is False
    
    @patch('sys.stdout.isatty')
    @patch('os.get_terminal_size')
    def test_validate_tui_environment_small_terminal(self, mock_term_size, mock_isatty):
        """Test TUI environment validation failure - terminal too small."""
        mock_isatty.return_value = True
        mock_term_size.return_value = os.terminal_size((5, 20))  # Too small
        
        result = validate_tui_environment()
        assert result is False