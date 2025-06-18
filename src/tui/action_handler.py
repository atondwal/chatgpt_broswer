#!/usr/bin/env python3
"""Base classes for action handling in the TUI."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Any, Tuple


class ActionContext:
    """Context information passed to action handlers."""
    
    def __init__(self, tui, key: int, result: str):
        """Initialize action context.
        
        Args:
            tui: The TUI instance
            key: The key that was pressed
            result: The result from tree_view.handle_input()
        """
        self.tui = tui
        self.key = key
        self.result = result
        self.tree_view = tui.tree_view
        self.selected_item = tui.tree_view.get_selected()
        self.selected_items = tui.selected_items
        self.tree_items = tui.tree_items
        self.tree = tui.tree
        self.stdscr = getattr(tui, 'stdscr', None)
        
        
class ActionResult:
    """Result returned by action handlers."""
    
    def __init__(self, 
                 success: bool,
                 message: str = "",
                 refresh_tree: bool = False,
                 save_tree: bool = False,
                 change_view: Optional[Any] = None,
                 clear_selection: bool = False):
        """Initialize action result.
        
        Args:
            success: Whether the action succeeded
            message: Status message to display
            refresh_tree: Whether to refresh the tree view
            save_tree: Whether to save the tree
            change_view: New view mode to switch to
            clear_selection: Whether to clear selection
        """
        self.success = success
        self.message = message
        self.refresh_tree = refresh_tree
        self.save_tree = save_tree
        self.change_view = change_view
        self.clear_selection = clear_selection
        

class ActionHandler(ABC):
    """Abstract base class for action handlers."""
    
    @abstractmethod
    def can_handle(self, action: str) -> bool:
        """Check if this handler can process the action.
        
        Args:
            action: The action string to check
            
        Returns:
            True if this handler can process the action
        """
        pass
        
    @abstractmethod
    def handle(self, action: str, context: ActionContext) -> Optional[ActionResult]:
        """Handle the action and return result.
        
        Args:
            action: The action to handle
            context: The action context
            
        Returns:
            ActionResult if handled, None if not handled
        """
        pass