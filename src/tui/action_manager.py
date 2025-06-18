#!/usr/bin/env python3
"""Action management for undo/redo functionality."""

from typing import List, Tuple, Any, Optional
from src.tui.action_handler import ActionHandler, ActionContext, ActionResult


class ActionManager(ActionHandler):
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
        
    # ActionHandler implementation
    def can_handle(self, action: str) -> bool:
        """Check if this handler can process the action."""
        return action in {"undo", "repeat", "copy", "paste"}
        
    def handle(self, action: str, context: ActionContext) -> Optional[ActionResult]:
        """Handle undo/redo/copy/paste actions."""
        if action == "undo":
            undo_info = self.get_undo_action()
            if not undo_info:
                return ActionResult(True, message="Nothing to undo")
                
            action_type, data = undo_info
            
            # Process the undo based on action type
            try:
                if action_type == "move":
                    # Undo move: move back to original position
                    node_id, original_parent = data
                    context.tree.move_node(node_id, original_parent)
                    return ActionResult(True, message="Undid move operation", 
                                      save_tree=True, refresh_tree=True)
                                      
                elif action_type in ("indent", "outdent"):
                    # Undo indent/outdent: restore all items to original positions
                    original_positions = data
                    for item_id, original_parent in original_positions:
                        if item_id in context.tree.nodes:
                            context.tree.move_node(item_id, original_parent)
                    return ActionResult(True, message=f"Undid {action_type} operation",
                                      save_tree=True, refresh_tree=True)
                                      
                elif action_type == "create":
                    # Undo create: delete the created item
                    node_id = data
                    if node_id in context.tree.nodes:
                        context.tree.delete_node(node_id)
                        return ActionResult(True, message="Undid create operation",
                                          save_tree=True, refresh_tree=True)
                                          
                else:
                    return ActionResult(False, message=f"Cannot undo action: {action_type}")
                    
            except Exception as e:
                return ActionResult(False, message=f"Undo failed: {e}")
                
        elif action == "repeat":
            last_action = self.get_last_action()
            if not last_action:
                return ActionResult(True, message="No action to repeat")
                
            action_type, _ = last_action
            
            if action_type == "move_up" and context.selected_item:
                node, _, _ = context.selected_item
                if context.tree.move_item_up(node.id):
                    self.save_last_action("move_up")
                    return ActionResult(True, message=f"Repeated: moved '{node.name}' up",
                                      save_tree=True, refresh_tree=True)
                                      
            elif action_type == "move_down" and context.selected_item:
                node, _, _ = context.selected_item
                if context.tree.move_item_down(node.id):
                    self.save_last_action("move_down")
                    return ActionResult(True, message=f"Repeated: moved '{node.name}' down",
                                      save_tree=True, refresh_tree=True)
                                      
            return ActionResult(False, message=f"Cannot repeat action: {action_type}")
            
        elif action == "copy":
            if context.selected_item:
                node, conv, _ = context.selected_item
                title = conv.title if conv else node.name
                # Store in TUI's clipboard attribute
                context.tui.clipboard = {"type": "title", "data": title}
                return ActionResult(True, message=f"Copied: {title[:30]}...")
            return ActionResult(False, message="Nothing to copy")
            
        elif action == "paste":
            if hasattr(context.tui, 'clipboard') and context.tui.clipboard:
                return ActionResult(True, message=f"Paste: {context.tui.clipboard['data'][:30]}...")
            return ActionResult(True, message="Nothing to paste")
            
        return None