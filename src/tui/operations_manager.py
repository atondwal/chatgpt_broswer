#!/usr/bin/env python3
"""Operations management for folder and item operations."""

from typing import Set, List, Tuple, Any, Optional
from src.tui.input import get_input


class OperationsManager:
    """Manages folder and item operations like create, move, delete, rename."""
    
    def __init__(self, tree, stdscr):
        self.tree = tree
        self.stdscr = stdscr
        
    def create_folder(self, selected_items: Set[str], current_item: Optional[Tuple[Any, Any, int]] = None) -> Tuple[str, Set[str]]:
        """Create new folder and optionally move selected items into it.
        
        Returns:
            Tuple of (status_message, cleared_selection)
        """
        name = get_input(self.stdscr, "Folder name:")
        if not name:
            return "Folder creation cancelled", selected_items
            
        try:
            parent_id = None
            if current_item:
                node, _, _ = current_item
                if node.is_folder:
                    parent_id = node.id
                    
            folder_id = self.tree.create_folder(name, parent_id)
            
            # If we have selected items, move them into the new folder
            if selected_items:
                moved_items = []
                for item_id in selected_items.copy():  # Copy to avoid modification during iteration
                    try:
                        self.tree.move_node(item_id, folder_id)
                        moved_items.append(self.tree.nodes[item_id].name)
                    except Exception:
                        pass  # Skip items that can't be moved
                
                if moved_items:
                    status = f"Created '{name}' and moved {len(moved_items)} items into it"
                else:
                    status = f"Created '{name}' (no items could be moved)"
                    
                # Clear selection after moving
                return status, set()
            else:
                return f"Created '{name}'", selected_items
                
        except Exception as e:
            return f"Error: {e}", selected_items
            
    def rename_item(self, current_item: Optional[Tuple[Any, Any, int]]) -> str:
        """Rename the selected item.
        
        Returns:
            Status message
        """
        if not current_item:
            return "No item selected to rename"
            
        node, _, _ = current_item
        current_name = node.name
        new_name = get_input(self.stdscr, f"Rename '{current_name}' to:", current_name)
        
        if not new_name or new_name == current_name:
            return "Rename cancelled"
            
        try:
            self.tree.rename_node(node.id, new_name)
            return f"Renamed '{current_name}' to '{new_name}'"
        except Exception as e:
            return f"Error: {e}"
            
    def delete_item(self, current_item: Optional[Tuple[Any, Any, int]]) -> str:
        """Delete the selected item.
        
        Returns:
            Status message
        """
        if not current_item:
            return "No item selected to delete"
            
        node, _, _ = current_item
        try:
            self.tree.delete_node(node.id)
            return f"Deleted '{node.name}'"
        except Exception as e:
            return f"Error: {e}"
            
    def move_item(self, current_item: Optional[Tuple[Any, Any, int]]) -> str:
        """Move the selected item to a different folder.
        
        Returns:
            Status message
        """
        if not current_item:
            return "No item selected to move"
            
        from src.tui.input import select_folder
        
        node, _, _ = current_item
        target_folder = select_folder(self.stdscr, self.tree, f"Move '{node.name}' to:")
        
        if target_folder is None:
            return "Move cancelled"
            
        try:
            self.tree.move_node(node.id, target_folder)
            target_name = self.tree.nodes[target_folder].name if target_folder else "Root"
            return f"Moved '{node.name}' to '{target_name}'"
        except Exception as e:
            return f"Error: {e}"
            
    def indent_items(self, selected_items: Set[str], current_item: Optional[Tuple[Any, Any, int]]) -> Tuple[str, List[Tuple[str, str]]]:
        """Indent selected items (move them into a sibling folder).
        
        Returns:
            Tuple of (status_message, original_positions_for_undo)
        """
        if not selected_items:
            return "No items selected to indent", []
            
        # Find a suitable folder to move items into
        if not current_item:
            return "Cannot determine target for indentation", []
            
        current_node, _, _ = current_item
        
        # Look for a folder at the same level to move items into
        parent_id = current_node.parent_id
        siblings = self.tree.nodes[parent_id].children if parent_id else self.tree.root_nodes
        
        # Find first folder sibling
        target_folder = None
        for sibling_id in siblings:
            sibling = self.tree.nodes.get(sibling_id)
            if sibling and sibling.is_folder and sibling_id not in selected_items:
                target_folder = sibling_id
                break
                
        if not target_folder:
            return "No folder available for indentation", []
            
        # Save original positions for undo
        original_positions = []
        for item_id in selected_items:
            if item_id in self.tree.nodes:
                node = self.tree.nodes[item_id]
                original_positions.append((item_id, node.parent_id))
        
        moved = 0
        for item_id in selected_items:
            try:
                self.tree.move_node(item_id, target_folder)
                moved += 1
            except Exception:
                pass
                
        if moved > 0:
            return f"Indented {moved} items into folder", original_positions
        else:
            return "Could not indent items", []
            
    def outdent_items(self, selected_items: Set[str]) -> Tuple[str, List[Tuple[str, str]]]:
        """Outdent selected items (move them to parent level).
        
        Returns:
            Tuple of (status_message, original_positions_for_undo)
        """
        if not selected_items:
            return "No items selected to outdent", []
            
        # Save original positions for undo
        original_positions = []
        for item_id in selected_items:
            if item_id in self.tree.nodes:
                node = self.tree.nodes[item_id]
                original_positions.append((item_id, node.parent_id))
            
        moved = 0
        for item_id in selected_items:
            node = self.tree.nodes.get(item_id)
            if node and node.parent_id:
                # Move to the parent's parent
                grandparent_id = self.tree.nodes[node.parent_id].parent_id if node.parent_id in self.tree.nodes else None
                try:
                    self.tree.move_node(item_id, grandparent_id)
                    moved += 1
                except Exception:
                    pass
                    
        if moved > 0:
            return f"Outdented {moved} items", original_positions
        else:
            return "Could not outdent items (already at top level?)", []
            
    def bulk_move_up(self, selected_items: Set[str], tree_items: List[Tuple[Any, Any, int]]) -> str:
        """Move all selected items up.
        
        Returns:
            Status message
        """
        if not selected_items:
            return "No items selected to move"
            
        # Get items in tree order
        selected_in_order = []
        for node, _, _ in tree_items:
            if node.id in selected_items:
                selected_in_order.append(node.id)
                
        # Move from top to bottom to maintain relative order
        moved = 0
        for item_id in selected_in_order:
            if self.tree.move_item_up(item_id):
                moved += 1
                
        return f"Moved {moved} items up" if moved > 0 else "Could not move items up"
        
    def bulk_move_down(self, selected_items: Set[str], tree_items: List[Tuple[Any, Any, int]]) -> str:
        """Move all selected items down.
        
        Returns:
            Status message
        """
        if not selected_items:
            return "No items selected to move"
            
        # Get items in tree order
        selected_in_order = []
        for node, _, _ in tree_items:
            if node.id in selected_items:
                selected_in_order.append(node.id)
                
        # Move from bottom to top to maintain relative order
        moved = 0
        for item_id in reversed(selected_in_order):
            if self.tree.move_item_down(item_id):
                moved += 1
                
        return f"Moved {moved} items down" if moved > 0 else "Could not move items down"