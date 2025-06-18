#!/usr/bin/env python3
"""Action management for undo/redo functionality."""

from typing import List, Tuple, Any, Optional


class ActionManager:
    """Manages undo/redo system and action recording."""
    
    def __init__(self, max_undo_size: int = 20):
        # Undo system
        self.undo_stack: List[Tuple[str, Any]] = []  # Stack of (action, data) tuples
        self.last_action: Optional[Tuple[str, Any]] = None  # Last action for repeat
        self.max_undo_size = max_undo_size
        
    def save_undo_state(self, action: str, data: Any) -> None:
        """Save state for undo functionality."""
        self.undo_stack.append((action, data))
        
        # Limit undo stack size
        if len(self.undo_stack) > self.max_undo_size:
            self.undo_stack.pop(0)
            
    def save_last_action(self, action_type: str, action_data: Any = None) -> None:
        """Save last action for repeat functionality."""
        self.last_action = (action_type, action_data)
        
    def get_undo_action(self) -> Optional[Tuple[str, Any]]:
        """Get the next action to undo.
        
        Returns:
            Tuple of (action, data) or None if nothing to undo
        """
        if self.undo_stack:
            return self.undo_stack.pop()
        return None
        
    def get_last_action(self) -> Optional[Tuple[str, Any]]:
        """Get the last action for repeat functionality.
        
        Returns:
            Tuple of (action_type, action_data) or None if no last action
        """
        return self.last_action
        
    def has_undo_actions(self) -> bool:
        """Check if there are actions available to undo."""
        return len(self.undo_stack) > 0
        
    def has_last_action(self) -> bool:
        """Check if there's a last action available to repeat."""
        return self.last_action is not None
        
    def clear_undo_stack(self) -> None:
        """Clear the undo stack."""
        self.undo_stack.clear()
        
    def get_undo_count(self) -> int:
        """Get the number of actions in the undo stack."""
        return len(self.undo_stack)