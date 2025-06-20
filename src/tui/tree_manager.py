#!/usr/bin/env python3
"""Tree management operations for the TUI interface."""

import os
import tempfile
import subprocess
from typing import Optional, Any
from src.tui.action_handler import ActionHandler, ActionContext, ActionResult
from src.core.exporter import export_conversation


class TreeManager(ActionHandler):
    """Manages tree-specific operations like expand/collapse and filtering."""
    
    def __init__(self, tree, tui):
        self.tree = tree
        self.tui = tui
        
    # ActionHandler implementation
    def can_handle(self, action: str) -> bool:
        """Check if this handler can process the action."""
        actions = {"select", "toggle", "expand_all", "collapse_all",
                   "filter_folders", "filter_conversations", "show_all",
                   "toggle_sort", "clear_custom_order", "refresh", "help"}
        return action in actions or action.startswith("expand_depth_")
        
    def handle(self, action: str, context: ActionContext) -> Optional[ActionResult]:
        """Handle tree-specific actions."""
        if action == "select":
            if not context.selected_item:
                return ActionResult(False)
            
            node, conv, _ = context.selected_item
            if node.is_folder:
                self.tree.toggle_folder(node.id)
                return ActionResult(True, refresh_tree=True)
            elif conv:
                # Open conversation in editor
                self._open_in_editor(conv)
                return ActionResult(True)
                
        elif action == "toggle":
            if context.selected_item:
                node, _, _ = context.selected_item
                if node.is_folder:
                    self.tree.toggle_folder(node.id)
                    return ActionResult(True, refresh_tree=True)
                    
        elif action == "expand_all":
            for node in self.tree.nodes.values():
                if node.is_folder:
                    node.expanded = True
            return ActionResult(True, refresh_tree=True)
            
        elif action == "collapse_all":
            for node in self.tree.nodes.values():
                if node.is_folder:
                    node.expanded = False
            return ActionResult(True, refresh_tree=True)
            
        elif action.startswith("expand_depth_"):
            depth = int(action.split("_")[-1])
            self._expand_to_depth(depth)
            if depth == 0:
                message = "Collapsed all folders"
            else:
                message = f"Expanded to depth {depth}"
            return ActionResult(True, message=message, refresh_tree=True)
            
        elif action == "filter_folders":
            # Filter conversations to empty, keeping only folder structure
            context.tui.filtered_conversations = []
            return ActionResult(True, message="Showing only folders", refresh_tree=True)
            
        elif action == "filter_conversations":
            # This would need more complex logic to flatten the tree
            return ActionResult(True, message="Showing only conversations")
            
        elif action == "show_all":
            context.tui.filtered_conversations = context.tui.conversations
            return ActionResult(True, message="Showing all items", refresh_tree=True)
            
        elif action == "toggle_sort":
            context.tui.sort_by_date = not context.tui.sort_by_date
            sort_type = "date" if context.tui.sort_by_date else "alphabetical"
            return ActionResult(True, message=f"Sorting by {sort_type}", refresh_tree=True)
            
        elif action == "clear_custom_order":
            self.tree.clear_custom_order()
            return ActionResult(True, message="Cleared custom ordering", 
                              save_tree=True, refresh_tree=True)
                              
        elif action == "refresh":
            try:
                from src.core.loader import load_conversations
                context.tui.conversations = load_conversations(context.tui.conversations_file)
                context.tui.filtered_conversations = context.tui.conversations
                message = f"Refreshed {len(context.tui.conversations)} conversations"
                return ActionResult(True, message=message, refresh_tree=True)
            except Exception as e:
                return ActionResult(False, message=f"Refresh failed: {e}")
                
        elif action == "help":
            self._show_tree_help(context)
            return ActionResult(True)
            
        return None
        
    def _expand_to_depth(self, depth: int) -> None:
        """Expand tree to specific depth level."""
        if depth == 0:
            # Collapse all
            for node in self.tree.nodes.values():
                if node.is_folder:
                    node.expanded = False
        else:
            # Expand to specified depth
            def expand_recursive(node_ids, current_depth):
                for node_id in node_ids:
                    if node_id in self.tree.nodes:
                        node = self.tree.nodes[node_id]
                        if node.is_folder:
                            node.expanded = current_depth < depth
                            if node.expanded:
                                expand_recursive(node.children, current_depth + 1)
            
            expand_recursive(self.tree.root_nodes, 1)
            
    def _show_tree_help(self, context: ActionContext) -> None:
        """Show help dialog for tree view."""
        help_text = [
            "Enhanced Keybindings:",
            "",
            "Vim Navigation:",
            "  ↑/k, ↓/j   - Move up/down",
            "  gg, G      - Go to top/bottom",  
            "  Ctrl+D/U   - Half page down/up",
            "  Ctrl+F/B   - Full page down/up",
            "  H/M/L      - Jump High/Middle/Low on screen",
            "  h/l        - Jump to parent / Expand folder",
            "  zz         - Center current item",
            "",
            "Quick Actions:",
            "  x, dd      - Delete item",
            "  yy         - Copy title",
            "  p          - Paste",
            "  u          - Undo",
            "  .          - Repeat action",
            "",
            "Function Keys (may not work in all terminals):",
            "  F1 or ?    - Help (this screen)",
            "  F2 or r    - Rename item",
            "  F3 or f    - Filter/search",
            "  F5         - Refresh tree",
            "  Delete/x   - Delete item",
            "  Insert     - New folder",
            "",
            "Multi-select:",
            "  Space      - Select/deselect",
            "  Ctrl+A     - Select all",
            "  V          - Visual mode",
            "",
            "Search/Filter:",
            "  /          - Vim-style search",
            "  f          - Filter mode",
            "  n/N        - Next/prev match",
            "  Ctrl+G     - Next match (in search)",
            "",
            "Organization:",
            "  Tab/S-Tab  - Indent/outdent",
            "  Alt+↑/↓    - Move item up/down",
            "  n          - New folder",
            "  r          - Rename",
            "  m          - Move to folder",
            "  o/O        - Sort order/Clear custom",
            "",
            "View Control:",
            "  Enter      - Open conversation in editor/toggle folder",
            "  E          - Expand all",
            "  C          - Collapse all", 
            "  1-5        - Expand to depth",
            "  0          - Collapse all",
            "",
            "Press any key to close..."
        ]
        
        # Show help using curses window
        import curses
        h, w = context.stdscr.getmaxyx()
        height = min(len(help_text) + 2, h - 2)
        width = min(max(len(line) for line in help_text) + 4, w - 4)
        start_y = (h - height) // 2
        start_x = (w - width) // 2
        
        help_win = curses.newwin(height, width, start_y, start_x)
        help_win.box()
        
        for i, line in enumerate(help_text[:height - 2]):
            if i == 0:
                help_win.addstr(i + 1, 2, line, curses.A_BOLD)
            else:
                help_win.addstr(i + 1, 2, line)
                
        help_win.refresh()
        help_win.getch()  # Wait for any key
        del help_win
        
    def _open_in_editor(self, conversation) -> None:
        """Open conversation in user's editor."""
        # Export conversation to temp file
        content = export_conversation(conversation, format="markdown")
        
        # Create temp file with .md extension for syntax highlighting
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            # Get editor from environment or use sensible defaults
            editor = os.environ.get('EDITOR', 'vi')
            if not editor:
                # Try common editors
                for ed in ['nano', 'vim', 'vi', 'emacs', 'less']:
                    if subprocess.run(['which', ed], capture_output=True).returncode == 0:
                        editor = ed
                        break
                else:
                    editor = 'less'  # Fallback to less for viewing
            
            # Suspend curses temporarily
            import curses
            curses.endwin()
            
            # Open in editor
            subprocess.run([editor, temp_path])
            
            # Resume curses
            curses.doupdate()
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass