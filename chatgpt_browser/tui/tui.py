#!/usr/bin/env python3
"""Refactored Terminal UI for browsing ChatGPT conversations."""

import argparse
import curses
import sys
from pathlib import Path

from chatgpt_browser.core.claude_loader import find_claude_project_for_cwd, list_claude_projects
from chatgpt_browser.core.logging_config import setup_logging, get_logger
from chatgpt_browser.core.curses_context import curses_context, emergency_cleanup
from chatgpt_browser.tui.tui_state import TUIInitializer, ManagerRegistry, UIState, ViewMode, validate_tui_environment
from chatgpt_browser.tui.tui_utils import ActionDispatcher, ViewRenderer, InputHandler, TreeUpdater, create_action_context
from chatgpt_browser.tui.tree_view import TreeView
from chatgpt_browser.tui.search_overlay import SearchOverlay
from chatgpt_browser.tui.action_handler import ActionContext, ActionResult


class TUI:
    """Refactored Terminal interface for browsing ChatGPT conversations."""
    
    def __init__(self, conversations_file: str, debug: bool = False, format: str = "auto"):
        self.logger = get_logger(__name__)
        
        # Validate environment
        if not validate_tui_environment():
            raise RuntimeError("Environment not suitable for TUI operation")
        
        # Initialize data
        self.initializer = TUIInitializer(conversations_file, debug, format)
        self.conversations, self.tree = self.initializer.initialize_data()
        self.ui_state = self.initializer.create_initial_state(self.conversations)
        
        # Initialize components (will be set up in run())
        self.stdscr = None
        self.tree_view = None
        self.search_overlay = None
        self.manager_registry = ManagerRegistry()
        self.action_dispatcher = None
        self.view_renderer = None
        self.input_handler = None
        self.tree_updater = None
    
    def run(self, stdscr) -> None:
        """Main UI loop with improved structure."""
        self.stdscr = stdscr
        
        try:
            self._setup_ui_components()
            self._setup_initial_state()
            self._main_loop()
            
        except Exception as e:
            self.logger.error(f"Error in main UI loop: {e}")
            if self.ui_state.debug:
                raise
            self.ui_state.status_message = f"Fatal error: {str(e)[:50]}"
    
    def _setup_ui_components(self) -> None:
        """Initialize UI components and managers."""
        # Setup colors
        self.initializer.setup_colors(self.stdscr)
        
        # Initialize UI components
        self.tree_view = TreeView(self.stdscr)
        height, width = self.stdscr.getmaxyx()
        self.search_overlay = SearchOverlay(self.stdscr, 0, 0, width)
        
        # Initialize utility classes
        self.view_renderer = ViewRenderer(self.stdscr)
        self.input_handler = InputHandler(self.tree_view)
        self.tree_updater = TreeUpdater(self.conversations, self.tree)
        
        # Register managers
        managers = self.manager_registry.register_managers(
            self.stdscr, self.ui_state, self.conversations, self.tree
        )
        self.action_dispatcher = ActionDispatcher(managers)
        
        self.logger.info("UI components initialized successfully")
    
    def _setup_initial_state(self) -> None:
        """Setup initial UI state."""
        try:
            self.tree_updater.refresh_tree_items(self.ui_state)
            self.logger.debug("Initial tree state refreshed")
            
        except Exception as e:
            self.logger.error(f"Error setting up initial state: {e}")
            if self.ui_state.debug:
                raise
            self.ui_state.status_message = f"Tree init error: {str(e)}"
    
    def _main_loop(self) -> None:
        """Main event loop."""
        while self.ui_state.running:
            try:
                # Render current view
                self.view_renderer.render_view(self.ui_state, self.tree_view, self.search_overlay)
                
                # Get user input and action
                action = self._get_next_action()
                if action:
                    self._handle_action(action)
                    
            except KeyboardInterrupt:
                self.logger.info("User interrupted application")
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                if self.ui_state.debug:
                    raise
                self.ui_state.status_message = f"Error: {str(e)[:50]}"
    
    def _get_next_action(self) -> str:
        """Get the next action from user input."""
        if self.ui_state.current_view == ViewMode.SEARCH:
            return self._handle_search_input()
        else:
            return self.input_handler.get_action(self.ui_state)
    
    def _handle_search_input(self) -> str:
        """Handle input in search mode."""
        from chatgpt_browser.tui.key_mapper import get_key_with_escape_handling
        
        try:
            key = get_key_with_escape_handling(self.stdscr)
            result = self.search_overlay.handle_input(key)
            
            if result == "search_cancelled":
                self.search_overlay.deactivate()
                self.ui_state.current_view = ViewMode.TREE
                self._clear_search()
                return None
                
            elif result == "search_submitted":
                self.search_overlay.deactivate()
                self.ui_state.current_view = ViewMode.TREE
                term = self.search_overlay.get_search_term()
                self._apply_search_term(term)
                return None
                
        except Exception as e:
            self.logger.error(f"Error handling search input: {e}")
            
        return None
    
    def _handle_action(self, action: str) -> None:
        """Handle a dispatched action."""
        # Create action context
        context = create_action_context(self.ui_state, self.conversations, self.tree)
        
        # Dispatch action
        result = self.action_dispatcher.dispatch_action(action, context)
        
        # Process result
        self._process_action_result(result, action)
    
    def _process_action_result(self, result: ActionResult, action: str) -> None:
        """Process the result of an action."""
        if result.message:
            self.ui_state.status_message = result.message
        
        # Handle state changes
        if result.refresh_tree:
            self.tree_updater.refresh_tree_items(self.ui_state)
        
        if result.quit_requested:
            self.ui_state.running = False
        
        # Handle view mode changes
        if action == "search":
            self.ui_state.current_view = ViewMode.SEARCH
            self.search_overlay.activate()
        elif action == "filter":
            self.ui_state.current_view = ViewMode.SEARCH
            self.search_overlay.activate(filter_mode=True)
    
    def _apply_search_term(self, term: str) -> None:
        """Apply search term and update UI state."""
        self.ui_state.search_term = term
        
        # Filter conversations based on search term
        if term:
            self.ui_state.filtered_conversations = [
                conv for conv in self.conversations
                if term.lower() in conv.title.lower()
            ]
        else:
            self.ui_state.filtered_conversations = self.conversations
        
        # Refresh tree with filtered conversations
        self.tree_updater.refresh_tree_items(self.ui_state)
        self.ui_state.tree_selected = 0
        self.ui_state.tree_offset = 0
    
    def _clear_search(self) -> None:
        """Clear search state."""
        self.ui_state.search_term = ""
        self.ui_state.filtered_conversations = self.conversations
        self.tree_updater.refresh_tree_items(self.ui_state)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="ChatGPT History Browser")
    parser.add_argument("conversations_file", nargs="?", help="Path to conversations file or Claude project")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--format", choices=["auto", "chatgpt", "claude"], default="auto",
                       help="Conversation format (auto-detected by default)")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(debug_mode=args.debug)
    logger = get_logger(__name__)
    
    # Auto-detect Claude project if no file specified
    if not args.conversations_file:
        # Check if we're in a Claude project directory
        claude_project = find_claude_project_for_cwd()
        if claude_project:
            args.conversations_file = claude_project
            args.format = "claude"
        else:
            # Fall back to showing Claude project picker
            projects = list_claude_projects()
            if not projects:
                print("No Claude projects found and no conversation file specified.")
                print("Please provide a conversation file path or create a Claude project.")
                sys.exit(1)
            
            print("No conversation file specified. Available Claude projects:")
            print("=" * 50)
            for i, project in enumerate(projects, 1):
                name = project['name']
                # Clean up project name and add leading slash
                if name.startswith('-'):
                    clean_name = '/' + name[1:].replace('-', '/')
                else:
                    clean_name = '/' + name.replace('-', '/')
                count = project['conversation_count']
                print(f"{i:2}. {clean_name} ({count} conversations)")
            
            print("\nUse: cgpt-tui ~/.claude/projects/<PROJECT_NAME>")
            print("  or: cgpt-tui <project_number>")
            try:
                choice = input("\nEnter project number or full path: ").strip()
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(projects):
                        args.conversations_file = projects[idx]['path']
                        args.format = "claude"
                    else:
                        print(f"Invalid project number. Must be 1-{len(projects)}")
                        sys.exit(1)
                else:
                    # Treat as file path
                    args.conversations_file = choice
            except (KeyboardInterrupt, EOFError):
                print("\nCancelled.")
                sys.exit(0)
    
    if not Path(args.conversations_file).exists():
        print(f"File not found: {args.conversations_file}")
        sys.exit(1)
    
    try:
        tui = TUI(args.conversations_file, debug=args.debug, format=args.format)
        with curses_context() as stdscr:
            tui.run(stdscr)
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        print("\nApplication interrupted.")
    except Exception as e:
        emergency_cleanup()
        logger.error(f"Application error: {e}")
        print(f"Error: {e}")
        if args.debug:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()