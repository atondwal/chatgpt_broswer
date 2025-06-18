#!/usr/bin/env python3
"""Search and filter management for the TUI interface."""

from typing import List, Tuple, Any, Optional
from src.tui.action_handler import ActionHandler, ActionContext, ActionResult


class SearchManager(ActionHandler):
    """Manages search functionality including vim-style search and filtering."""
    
    def __init__(self):
        # Search state
        self.search_term: str = ""
        self.search_matches: List[int] = []  # List of indices for vim-style search
        self.current_match_index: int = -1  # Current position in search matches
        self.filter_mode: bool = False  # Whether we're in filter mode (f) vs search mode (/)
        
    def start_search_mode(self) -> str:
        """Start vim-style search mode (non-destructive)."""
        self.filter_mode = False
        return "Incremental search: type to find and jump to matches"
        
    def start_filter_mode(self) -> str:
        """Start filter mode (destructive)."""
        self.filter_mode = True
        return "Filter mode: type to filter conversations"
        
    def find_search_matches(self, term: str, tree_items: List[Tuple[Any, Any, int]]) -> List[int]:
        """Find all tree items that match the search term."""
        if not term:
            return []
            
        matches = []
        term_lower = term.lower()
        
        for i, (node, conv, _) in enumerate(tree_items):
            # Search in node name
            if term_lower in node.name.lower():
                matches.append(i)
                continue
                
            # Search in conversation title and content
            if conv:
                if term_lower in conv.title.lower():
                    matches.append(i)
                    continue
                    
                # Search in message content
                for message in conv.messages:
                    if term_lower in message.content.lower():
                        matches.append(i)
                        break
                        
        return matches
        
    def update_search(self, term: str, tree_items: List[Tuple[Any, Any, int]]) -> Tuple[bool, str]:
        """Update search with new term.
        
        Returns:
            Tuple of (has_matches, status_message)
        """
        self.search_term = term
        if term:
            self.search_matches = self.find_search_matches(term, tree_items)
            if self.search_matches:
                return True, f"Found {len(self.search_matches)} matches"
            else:
                return False, f"No matches for: {term}"
        else:
            self.search_matches = []
            self.current_match_index = -1
            return False, ""
            
    def jump_to_match(self, match_index: int) -> Tuple[Optional[int], str]:
        """Jump to a specific search match.
        
        Returns:
            Tuple of (tree_index_to_jump_to, status_message)
        """
        if 0 <= match_index < len(self.search_matches):
            tree_index = self.search_matches[match_index]
            self.current_match_index = match_index
            
            # Show match info
            total_matches = len(self.search_matches)
            status = f"Match {match_index + 1}/{total_matches}: {self.search_term}"
            return tree_index, status
        return None, ""
    
    def search_next(self) -> Tuple[Optional[int], str]:
        """Jump to next search match.
        
        Returns:
            Tuple of (tree_index_to_jump_to, status_message)
        """
        if not self.search_matches:
            return None, "No search results. Use / to search."
            
        next_index = (self.current_match_index + 1) % len(self.search_matches)
        return self.jump_to_match(next_index)
    
    def search_previous(self) -> Tuple[Optional[int], str]:
        """Jump to previous search match.
        
        Returns:
            Tuple of (tree_index_to_jump_to, status_message)
        """
        if not self.search_matches:
            return None, "No search results. Use / to search."
            
        prev_index = (self.current_match_index - 1) % len(self.search_matches)
        return self.jump_to_match(prev_index)
        
    def clear_search(self) -> None:
        """Clear search state."""
        self.search_term = ""
        self.search_matches = []
        self.current_match_index = -1
        
    def get_match_count(self) -> int:
        """Get the number of current search matches."""
        return len(self.search_matches)
        
    def is_filter_mode(self) -> bool:
        """Check if we're in filter mode."""
        return self.filter_mode
        
    def has_matches(self) -> bool:
        """Check if there are any search matches."""
        return len(self.search_matches) > 0
        
    # ActionHandler implementation
    def can_handle(self, action: str) -> bool:
        """Check if this handler can process the action."""
        return action in {"quick_filter", "search_next", "search_previous"}
        
    def handle(self, action: str, context: ActionContext) -> Optional[ActionResult]:
        """Handle search-related actions."""
        if action == "quick_filter":
            message = self.start_filter_mode()
            # The actual search overlay activation is handled in TUI
            return ActionResult(True, message=message)
            
        elif action == "search_next":
            tree_index, message = self.search_next()
            if tree_index is not None:
                context.tree_view.selected = tree_index
                context.tree_view._ensure_visible()
            return ActionResult(True, message=message)
            
        elif action == "search_previous":
            tree_index, message = self.search_previous()
            if tree_index is not None:
                context.tree_view.selected = tree_index
                context.tree_view._ensure_visible()
            return ActionResult(True, message=message)
            
        return None