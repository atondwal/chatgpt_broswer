#!/usr/bin/env python3
"""TUI state management and initialization utilities."""

from enum import Enum
from typing import List, Optional, Tuple
from dataclasses import dataclass, field

from chatgpt_browser.core.models import Conversation
from chatgpt_browser.tree.tree import TreeNode, ConversationTree
from chatgpt_browser.core.logging_config import get_logger

logger = get_logger(__name__)


class ViewMode(Enum):
    """Available view modes."""
    TREE = "tree"
    SEARCH = "search"


@dataclass
class UIState:
    """Container for TUI state variables."""
    
    # Core state
    conversations_file: str
    debug: bool = False
    current_view: ViewMode = ViewMode.TREE
    running: bool = True
    status_message: str = ""
    
    # Tree view state
    tree_items: List[Tuple[TreeNode, Optional[Conversation], int]] = field(default_factory=list)
    tree_offset: int = 0
    tree_selected: int = 0
    sort_by_date: bool = True
    
    # Search state
    search_term: str = ""
    filtered_conversations: List[Conversation] = field(default_factory=list)


class TUIInitializer:
    """Handles TUI initialization and data loading."""
    
    def __init__(self, conversations_file: str, debug: bool = False, format: str = "auto"):
        self.conversations_file = conversations_file
        self.debug = debug
        self.format = format
        self.logger = get_logger(__name__)
    
    def initialize_data(self) -> Tuple[List[Conversation], ConversationTree]:
        """
        Load conversations and initialize tree structure.
        
        Returns:
            Tuple of (conversations, tree)
        """
        try:
            from chatgpt_browser.core.loader import load_conversations
            
            conversations = load_conversations(self.conversations_file, format=self.format)
            tree = ConversationTree(self.conversations_file)
            
            self.logger.info(f"Loaded {len(conversations)} conversations")
            return conversations, tree
            
        except Exception as e:
            self.logger.error(f"Failed to initialize data: {e}")
            raise
    
    def create_initial_state(self, conversations: List[Conversation]) -> UIState:
        """
        Create initial UI state.
        
        Args:
            conversations: Loaded conversations
            
        Returns:
            Initialized UI state
        """
        state = UIState(
            conversations_file=self.conversations_file,
            debug=self.debug,
            filtered_conversations=conversations
        )
        
        self.logger.debug(f"Created initial UI state with {len(conversations)} conversations")
        return state
    
    def setup_colors(self, stdscr) -> None:
        """
        Setup color pairs for the TUI.
        
        Args:
            stdscr: Curses screen object
        """
        import curses
        
        try:
            curses.start_color()
            curses.use_default_colors()
            
            # Define color pairs
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Selected
            curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)   # Status
            curses.init_pair(3, curses.COLOR_YELLOW, -1)                 # Folder
            
            self.logger.debug("Color pairs initialized successfully")
            
        except curses.error as e:
            self.logger.warning(f"Failed to initialize colors: {e}")


class ManagerRegistry:
    """Registry for TUI action managers."""
    
    def __init__(self):
        self.managers = []
        self.logger = get_logger(__name__)
    
    def register_managers(self, stdscr, ui_state: UIState, conversations: List[Conversation], tree: ConversationTree):
        """
        Register and initialize all action managers.
        
        Args:
            stdscr: Curses screen object
            ui_state: UI state container
            conversations: Loaded conversations
            tree: Conversation tree
            
        Returns:
            List of initialized managers
        """
        from chatgpt_browser.tui.selection_manager import SelectionManager
        from chatgpt_browser.tui.search_manager import SearchManager
        from chatgpt_browser.tui.action_manager import ActionManager
        from chatgpt_browser.tui.fzf_search import FZFSearch
        from chatgpt_browser.tui.operations_manager import OperationsManager
        from chatgpt_browser.tui.tree_manager import TreeManager
        
        try:
            # Initialize managers that don't need stdscr
            self.managers = [
                SelectionManager(),
                SearchManager(), 
                ActionManager(),
                FZFSearch()
            ]
            
            # Initialize managers that need stdscr/tui context
            self.managers.extend([
                OperationsManager(stdscr, conversations, tree),
                TreeManager(stdscr, conversations, tree)
            ])
            
            self.logger.info(f"Registered {len(self.managers)} action managers")
            return self.managers
            
        except Exception as e:
            self.logger.error(f"Failed to register managers: {e}")
            raise
    
    def get_managers(self):
        """Get list of registered managers."""
        return self.managers


def validate_tui_environment() -> bool:
    """
    Validate that the environment supports TUI operation.
    
    Returns:
        True if environment is suitable for TUI
    """
    import sys
    import os
    
    logger = get_logger(__name__)
    
    # Check if running in a terminal
    if not sys.stdout.isatty():
        logger.warning("Not running in a terminal")
        return False
    
    # Check terminal size
    try:
        rows, cols = os.get_terminal_size()
        if rows < 10 or cols < 40:
            logger.warning(f"Terminal too small: {rows}x{cols} (minimum 10x40)")
            return False
    except OSError:
        logger.warning("Could not determine terminal size")
        return False
    
    # Check for TERM environment variable
    if not os.environ.get('TERM'):
        logger.warning("TERM environment variable not set")
        return False
    
    logger.debug("TUI environment validation passed")
    return True