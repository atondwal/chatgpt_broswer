#!/usr/bin/env python3
"""Operations management for folder and item operations."""

from typing import Set, List, Tuple, Any, Optional
from chatgpt_browser.tui.input import get_input, confirm, select_folder
from chatgpt_browser.tui.action_handler import ActionHandler, ActionContext, ActionResult


class OperationsManager(ActionHandler):
    """Manages folder and item operations like create, move, delete, rename."""
    
    def __init__(self, tree, stdscr):
        self.tree = tree
        self.stdscr = stdscr
        
    def create_folder(self, selected_items: Set[str], current_item: Optional[Tuple[Any, Any, int]] = None) -> Tuple[str, bool, Optional[str]]:
        """Create new folder and optionally move selected items into it.
        
        Returns:
            Tuple of (status_message, should_clear_selection, folder_id)
        """
        name = get_input(self.stdscr, "Folder name:")
        if not name:
            return "Folder creation cancelled", False, None
            
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
                return status, True, folder_id
            else:
                return f"Created '{name}'", False, folder_id
                
        except Exception as e:
            return f"Error: {e}", False, None
            
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
            
        from chatgpt_browser.tui.input import select_folder
        
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
        # If no items selected, use current item
        if not selected_items and current_item:
            current_node, _, _ = current_item
            selected_items = {current_node.id}
        elif not selected_items:
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
            if moved == 1:
                return f"Indented item into folder", original_positions
            else:
                return f"Indented {moved} items into folder", original_positions
        else:
            return "Could not indent items", []
            
    def outdent_items(self, selected_items: Set[str], current_item: Optional[Tuple[Any, Any, int]] = None) -> Tuple[str, List[Tuple[str, str]]]:
        """Outdent selected items (move them to parent level).
        
        Returns:
            Tuple of (status_message, original_positions_for_undo)
        """
        # If no items selected, use current item
        if not selected_items and current_item:
            current_node, _, _ = current_item
            selected_items = {current_node.id}
        elif not selected_items:
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
            if moved == 1:
                return f"Outdented item", original_positions
            else:
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
        
    # ActionHandler implementation
    def can_handle(self, action: str) -> bool:
        """Check if this handler can process the action."""
        actions = {"new_folder", "rename", "delete", "move_up", "move_down", 
                   "indent", "outdent", "move", "bulk_move", "resume", "new_claude_code"}
        return action in actions
        
    def handle(self, action: str, context: ActionContext) -> Optional[ActionResult]:
        """Handle folder and item operations."""
        if action == "new_folder":
            message, should_clear_selection, folder_id = self.create_folder(
                context.selected_items.copy(), 
                context.selected_item
            )
            if "Created" in message and folder_id:
                # Save action for undo
                if hasattr(context.tui, 'action_manager'):
                    context.tui.action_manager.save_undo_state("create", folder_id)
                return ActionResult(True, message=message, save_tree=True, 
                                  refresh_tree=True, clear_selection=should_clear_selection)
            return ActionResult(False, message=message)
            
        elif action == "rename":
            message = self.rename_item(context.selected_item)
            if "Renamed" in message:
                return ActionResult(True, message=message, save_tree=True, refresh_tree=True)
            return ActionResult(False, message=message)
            
        elif action == "delete":
            if not context.selected_item:
                return ActionResult(False, message="No item selected to delete")
            node, _, _ = context.selected_item
            item_type = "folder" if node.is_folder else "conversation"
            
            if not confirm(context.stdscr, f"Delete {item_type} '{node.name}'?"):
                return ActionResult(False, message="Delete cancelled")
                
            message = self.delete_item(context.selected_item)
            if "Deleted" in message:
                return ActionResult(True, message=message, save_tree=True, refresh_tree=True)
            return ActionResult(False, message=message)
            
        elif action == "move":
            if context.selected_items:
                # Bulk move
                return self._handle_bulk_move(context)
            else:
                # Single item move
                message = self.move_item(context.selected_item)
                if "Moved" in message:
                    return ActionResult(True, message=message, save_tree=True, refresh_tree=True)
                return ActionResult(False, message=message)
                
        elif action == "move_up":
            if context.selected_items:
                message = self.bulk_move_up(context.selected_items, context.tree_items)
            else:
                if not context.selected_item:
                    return ActionResult(False, message="No item to move")
                node, _, _ = context.selected_item
                if self.tree.move_item_up(node.id):
                    context.tui.action_manager.save_last_action("move_up")
                    message = f"Moved '{node.name}' up"
                else:
                    return ActionResult(False, message="Cannot move up")
                    
            if "Moved" in message:
                return ActionResult(True, message=message, save_tree=True, refresh_tree=True)
            return ActionResult(False, message=message)
            
        elif action == "move_down":
            if context.selected_items:
                message = self.bulk_move_down(context.selected_items, context.tree_items)
            else:
                if not context.selected_item:
                    return ActionResult(False, message="No item to move")
                node, _, _ = context.selected_item
                if self.tree.move_item_down(node.id):
                    context.tui.action_manager.save_last_action("move_down")
                    message = f"Moved '{node.name}' down"
                else:
                    return ActionResult(False, message="Cannot move down")
                    
            if "Moved" in message:
                return ActionResult(True, message=message, save_tree=True, refresh_tree=True)
            return ActionResult(False, message=message)
            
        elif action == "indent":
            message, original_positions = self.indent_items(
                context.selected_items, 
                context.selected_item
            )
            if original_positions and hasattr(context.tui, 'action_manager'):
                context.tui.action_manager.save_undo_state("indent", original_positions)
            if "Indented" in message:
                return ActionResult(True, message=message, save_tree=True, 
                                  refresh_tree=True, clear_selection=True)
            return ActionResult(False, message=message)
            
        elif action == "outdent":
            message, original_positions = self.outdent_items(
                context.selected_items,
                context.selected_item
            )
            if original_positions and hasattr(context.tui, 'action_manager'):
                context.tui.action_manager.save_undo_state("outdent", original_positions)
            if "Outdented" in message:
                return ActionResult(True, message=message, save_tree=True, 
                                  refresh_tree=True, clear_selection=True)
            return ActionResult(False, message=message)
            
        elif action == "resume":
            return self._handle_resume(context)
            
        elif action == "new_claude_code":
            return self._handle_new_claude_code(context)
            
        return None
        
    def _handle_bulk_move(self, context: ActionContext) -> ActionResult:
        """Handle bulk move operation."""
        dest_id = select_folder(context.stdscr, context.tree_items)
        
        if dest_id is None:
            return ActionResult(False, message="Move cancelled")
            
        moved = 0
        for item_id in context.selected_items:
            if item_id != dest_id:  # Can't move to itself
                try:
                    self.tree.move_node(item_id, dest_id)
                    moved += 1
                except Exception:
                    pass  # Skip items that can't be moved
                    
        if moved > 0:
            dest_name = self.tree.nodes[dest_id].name if dest_id else "root"
            return ActionResult(True, 
                              message=f"Moved {moved} items to '{dest_name}'",
                              save_tree=True, 
                              refresh_tree=True, 
                              clear_selection=True)
        else:
            return ActionResult(False, message="No items could be moved")
            
    def _handle_resume(self, context: ActionContext) -> ActionResult:
        """Handle resuming a Claude conversation."""
        if not context.selected_item:
            return ActionResult(False, message="No conversation selected to resume")
            
        node, conv, _ = context.selected_item
        if node.is_folder:
            return ActionResult(False, message="Cannot resume a folder - select a conversation")
            
        if not conv:
            return ActionResult(False, message="No conversation data available")
            
        # Extract session ID from conversation
        session_id = getattr(conv, 'id', None) or getattr(conv, 'session_id', None)
        if not session_id:
            return ActionResult(False, message="No session ID found for this conversation")
            
            
        # Execute claude --resume command properly with ncurses
        import subprocess
        import curses
        import os
        from pathlib import Path
        # Properly end ncurses mode
        
        # Get the project directory from the conversation file path and run claude from there
        file_path = conv.metadata.get('file', '')
        cwd = None
        try:
            if file_path:
                # Decode project name back to original path
                project_dir = Path(file_path).parent
                project_name = project_dir.name
                if project_name.startswith('-'):
                    # Convert "-home-atondwal-playground" to "/home/atondwal/playground"
                    original_path = '/' + project_name[1:].replace('-', '/')
                    if Path(original_path).exists():
                        cwd = original_path
        finally:
            curses.endwin()
        
        # Run the claude command with the correct working directory
        # Use os.execvp to replace the current process entirely
        if cwd:
            os.chdir(cwd)
        os.system(f'claude --resume {session_id}')
            
    def _handle_new_claude_code(self, context: ActionContext) -> ActionResult:
        """Handle starting a new Claude Code session."""
        import subprocess
        import curses
        import os
        
        # Properly end ncurses mode
        curses.endwin()
        
        # Run the claude command
        os.system('claude')
        
        # Exit the TUI after launching Claude
        return ActionResult(True, message="Started new Claude Code session", exit_tui=True)
