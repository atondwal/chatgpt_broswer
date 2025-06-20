#!/usr/bin/env python3
"""TUI utility functions for action dispatch and main loop operations."""

import curses
from typing import List, Optional, Any, Dict

from chatgpt_browser.core.models import Conversation
from chatgpt_browser.tree.tree import ConversationTree
from chatgpt_browser.tui.action_handler import ActionContext, ActionResult
from chatgpt_browser.tui.tui_state import UIState, ViewMode
from chatgpt_browser.core.logging_config import get_logger

logger = get_logger(__name__)


class ActionDispatcher:
    """Handles action routing and execution."""
    
    def __init__(self, managers: List[Any]):
        self.managers = managers
        self.logger = get_logger(__name__)
    
    def dispatch_action(self, action: str, context: ActionContext) -> ActionResult:
        """
        Dispatch an action to the appropriate manager.
        
        Args:
            action: Action string to dispatch
            context: Action context with state and data
            
        Returns:
            ActionResult from the handling manager
        """
        self.logger.debug(f"Dispatching action: {action}")
        
        for manager in self.managers:
            if hasattr(manager, 'can_handle') and manager.can_handle(action):
                try:
                    result = manager.handle(action, context)
                    self.logger.debug(f"Action '{action}' handled by {manager.__class__.__name__}")
                    return result
                except Exception as e:
                    self.logger.error(f"Error handling action '{action}' in {manager.__class__.__name__}: {e}")
                    return ActionResult(False, message=f"Error: {e}")
        
        self.logger.warning(f"No handler found for action: {action}")
        return ActionResult(False, message=f"Unknown action: {action}")


class ViewRenderer:
    """Handles rendering of different view modes."""
    
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.logger = get_logger(__name__)
    
    def render_view(self, ui_state: UIState, tree_view, search_overlay) -> None:
        """
        Render the current view based on UI state.
        
        Args:
            ui_state: Current UI state
            tree_view: Tree view component
            search_overlay: Search overlay component
        """
        try:
            if ui_state.current_view == ViewMode.TREE:
                self._render_tree_view(tree_view, ui_state)
            elif ui_state.current_view == ViewMode.SEARCH:
                self._render_search_view(search_overlay, ui_state)
                
        except curses.error as e:
            self.logger.error(f"Curses error during rendering: {e}")
        except Exception as e:
            self.logger.error(f"Error rendering view: {e}")
    
    def _render_tree_view(self, tree_view, ui_state: UIState) -> None:
        """Render the tree view."""
        height, width = self.stdscr.getmaxyx()
        
        # Clear screen
        self.stdscr.clear()
        
        # Render tree
        tree_view.render(
            ui_state.tree_items, 
            ui_state.tree_selected, 
            ui_state.tree_offset, 
            height - 2  # Leave space for status
        )
        
        # Render status bar
        self._render_status_bar(ui_state, height, width)
        
        self.stdscr.refresh()
    
    def _render_search_view(self, search_overlay, ui_state: UIState) -> None:
        """Render the search overlay view."""
        search_overlay.render()
        self._render_status_bar(ui_state, *self.stdscr.getmaxyx())
        self.stdscr.refresh()
    
    def _render_status_bar(self, ui_state: UIState, height: int, width: int) -> None:
        """Render the status bar at the bottom of the screen."""
        status_text = ui_state.status_message or "Ready"
        
        try:
            # Clear status line
            self.stdscr.move(height - 1, 0)
            self.stdscr.clrtoeol()
            
            # Render status with background color
            self.stdscr.attron(curses.color_pair(2))
            self.stdscr.addstr(height - 1, 0, status_text[:width-1].ljust(width-1))
            self.stdscr.attroff(curses.color_pair(2))
            
        except curses.error:
            # Ignore errors when writing to edge of screen
            pass


class InputHandler:
    """Handles input processing and key mapping."""
    
    def __init__(self, tree_view):
        self.tree_view = tree_view
        self.logger = get_logger(__name__)
    
    def get_action(self, ui_state: UIState) -> Optional[str]:
        """
        Get the next action from user input.
        
        Args:
            ui_state: Current UI state
            
        Returns:
            Action string or None if no action
        """
        try:
            if ui_state.current_view == ViewMode.TREE:
                return self.tree_view.handle_input()
            elif ui_state.current_view == ViewMode.SEARCH:
                # Search overlay handles its own input
                return None
                
        except curses.error as e:
            self.logger.error(f"Input error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error handling input: {e}")
            return None


class TreeUpdater:
    """Handles tree state updates and refreshes."""
    
    def __init__(self, conversations: List[Conversation], tree: ConversationTree):
        self.conversations = conversations
        self.tree = tree
        self.logger = get_logger(__name__)
    
    def refresh_tree_items(self, ui_state: UIState) -> None:
        """
        Refresh the tree items based on current state.
        
        Args:
            ui_state: UI state to update
        """
        try:
            ui_state.tree_items = self._build_tree_items(ui_state.filtered_conversations, ui_state.sort_by_date)
            
            # Ensure selected index is valid
            if ui_state.tree_selected >= len(ui_state.tree_items):
                ui_state.tree_selected = max(0, len(ui_state.tree_items) - 1)
                
            self.logger.debug(f"Refreshed tree with {len(ui_state.tree_items)} items")
            
        except Exception as e:
            self.logger.error(f"Error refreshing tree items: {e}")
    
    def _build_tree_items(self, conversations: List[Conversation], sort_by_date: bool) -> List[tuple]:
        """Build the tree items list for display."""
        items = []
        
        # Add root nodes
        for node_id in self.tree.root_nodes:
            if node_id in self.tree.nodes:
                self._add_node_items(self.tree.nodes[node_id], conversations, items, 0, sort_by_date)
        
        # Add orphaned conversations
        orphaned = self._find_orphaned_conversations(conversations)
        for conv in orphaned:
            items.append((None, conv, 0))
        
        return items
    
    def _add_node_items(self, node, conversations: List[Conversation], items: List, depth: int, sort_by_date: bool) -> None:
        """Recursively add node items to the display list."""
        # Add the node itself
        conv = self._find_conversation_by_id(conversations, node.conversation_id) if node.conversation_id else None
        items.append((node, conv, depth))
        
        # Add children
        children = sorted(node.children, key=lambda child_id: self._get_sort_key(child_id, conversations, sort_by_date))
        for child_id in children:
            if child_id in self.tree.nodes:
                self._add_node_items(self.tree.nodes[child_id], conversations, items, depth + 1, sort_by_date)
    
    def _find_conversation_by_id(self, conversations: List[Conversation], conv_id: str) -> Optional[Conversation]:
        """Find conversation by ID."""
        for conv in conversations:
            if conv.id == conv_id:
                return conv
        return None
    
    def _find_orphaned_conversations(self, conversations: List[Conversation]) -> List[Conversation]:
        """Find conversations not represented in the tree."""
        tree_conv_ids = {node.conversation_id for node in self.tree.nodes.values() if node.conversation_id}
        return [conv for conv in conversations if conv.id not in tree_conv_ids]
    
    def _get_sort_key(self, node_id: str, conversations: List[Conversation], sort_by_date: bool):
        """Get sort key for a node."""
        if not sort_by_date:
            return self.tree.nodes[node_id].display_name.lower()
        
        if node_id in self.tree.nodes:
            node = self.tree.nodes[node_id]
            if node.conversation_id:
                conv = self._find_conversation_by_id(conversations, node.conversation_id)
                if conv and conv.update_time:
                    return -conv.update_time  # Negative for reverse chronological
        
        return 0


def create_action_context(tui_instance, key: int = 0, result: str = "") -> ActionContext:
    """
    Create an action context from TUI instance.
    
    Args:
        tui_instance: TUI instance with state
        key: Key pressed (optional)
        result: Result string (optional)
        
    Returns:
        ActionContext for manager operations
    """
    return ActionContext(
        tui=tui_instance,
        key=key,
        result=result
    )