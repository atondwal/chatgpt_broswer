#!/usr/bin/env python3
"""Selection management for the TUI interface."""

from typing import Set, Optional, List, Tuple, Any
from chatgpt_browser.tui.action_handler import ActionHandler, ActionContext, ActionResult


class SelectionManager(ActionHandler):
    """Manages selection state including visual mode and multi-select."""
    
    def __init__(self):
        # Multi-select state
        self.selected_items: Set[str] = set()  # Set of node IDs that are selected
        
        # Visual mode state
        self.visual_mode: bool = False  # Visual mode for range selection
        self.visual_start: Optional[int] = None  # Starting position for visual mode
        
    def clear_selection(self) -> None:
        """Clear all selected items."""
        self.selected_items.clear()
        
    def select_all(self, tree_items: List[Tuple[Any, Any, int]]) -> int:
        """Select all items in the tree."""
        self.selected_items.clear()
        for node, _, _ in tree_items:
            self.selected_items.add(node.id)
        return len(self.selected_items)
        
    def toggle_item_selection(self, node_id: str, node_name: str) -> Tuple[bool, str]:
        """Toggle selection of a specific item.
        
        Returns:
            Tuple of (is_now_selected, status_message)
        """
        if node_id in self.selected_items:
            self.selected_items.remove(node_id)
            return False, f"Deselected '{node_name}'"
        else:
            self.selected_items.add(node_id)
            return True, f"Selected '{node_name}'"
            
    def toggle_visual_mode(self, current_position: int, tree_items: List[Tuple[Any, Any, int]]) -> str:
        """Toggle visual selection mode.
        
        Returns:
            Status message
        """
        if not self.visual_mode:
            # Enter visual mode
            self.visual_mode = True
            self.visual_start = current_position
            # Start with current item selected
            if current_position < len(tree_items):
                node, _, _ = tree_items[current_position]
                self.selected_items.add(node.id)
            return "Visual mode activated - use arrows to select range"
        else:
            # Exit visual mode
            self.visual_mode = False
            self.visual_start = None
            return f"Visual mode deactivated - {len(self.selected_items)} items selected"
    
    def update_visual_selection(self, current_position: int, tree_items: List[Tuple[Any, Any, int]]) -> str:
        """Update selection based on visual mode range.
        
        Returns:
            Status message
        """
        if not self.visual_mode or self.visual_start is None:
            return ""
            
        # Clear previous selection and rebuild based on range
        self.selected_items.clear()
        
        start_pos = self.visual_start
        
        # Determine the range (inclusive)
        min_pos = min(start_pos, current_position)
        max_pos = max(start_pos, current_position)
        
        # Select all items in the range
        for i in range(min_pos, max_pos + 1):
            if i < len(tree_items):
                node, _, _ = tree_items[i]
                self.selected_items.add(node.id)
                
        # Update status to show selection size
        return f"Visual: {len(self.selected_items)} items selected"
        
    def has_selection(self) -> bool:
        """Check if any items are selected."""
        return len(self.selected_items) > 0
        
    def get_selection_count(self) -> int:
        """Get the number of selected items."""
        return len(self.selected_items)
        
    def get_selected_items(self) -> Set[str]:
        """Get the set of selected item IDs."""
        return self.selected_items.copy()
        
    # ActionHandler implementation
    def can_handle(self, action: str) -> bool:
        """Check if this handler can process the action."""
        return action in {"visual_mode", "select_all", "toggle_select", "clear_selection"}
        
    def handle(self, action: str, context: ActionContext) -> Optional[ActionResult]:
        """Handle selection-related actions."""
        if action == "visual_mode":
            message = self.toggle_visual_mode(
                context.tree_view.selected, 
                context.tree_items
            )
            return ActionResult(True, message=message)
            
        elif action == "select_all":
            count = self.select_all(context.tree_items)
            return ActionResult(True, message=f"Selected {count} items")
            
        elif action == "toggle_select":
            if context.selected_item:
                node, _, _ = context.selected_item
                _, message = self.toggle_item_selection(node.id, node.name)
                return ActionResult(True, message=message)
            return ActionResult(False, message="No item to select")
            
        elif action == "clear_selection":
            self.clear_selection()
            return ActionResult(True, message="Selection cleared")
            
        return None