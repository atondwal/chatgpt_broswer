#!/usr/bin/env python3
"""Base classes for action handling in the TUI."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any, Tuple


@dataclass
class ActionContext:
    """Context information passed to action handlers."""
    tui: Any
    key: int
    result: str
    tree_view: Any = field(init=False)
    selected_item: Any = field(init=False)
    selected_items: set = field(init=False)
    tree_items: list = field(init=False)
    tree: Any = field(init=False)
    stdscr: Any = field(init=False)
    
    def __post_init__(self):
        self.tree_view = self.tui.tree_view
        self.selected_item = self.tui.tree_view.get_selected()
        self.selected_items = self.tui.selection_manager.selected_items
        self.tree_items = self.tui.tree_items
        self.tree = self.tui.tree
        self.stdscr = getattr(self.tui, 'stdscr', None)


@dataclass
class ActionResult:
    """Result returned by action handlers."""
    success: bool
    message: str = ""
    refresh_tree: bool = False
    save_tree: bool = False
    change_view: Optional[Any] = None
    clear_selection: bool = False
        

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