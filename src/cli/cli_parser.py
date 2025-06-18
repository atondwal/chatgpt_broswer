#!/usr/bin/env python3
"""
Command-line interface parsing module for the legacy CLI interface.

Handles command-line argument parsing and routing to appropriate functionality.
"""

import sys
from typing import Any, Dict, List, Optional
from src.cli.cli_config import HISTORY_PATH
from src.cli.cli_data_loader import load_history, analyze_conversation
from src.cli.cli_export_formats import export_conversation, list_conversations
from src.cli.cli_search import search_conversations, display_search_results, get_search_result_by_index


def show_usage() -> None:
    """Display usage information."""
    print("Usage:")
    print("  python cgpt.py list [count]                                - List conversations")
    print("  python cgpt.py export <number> [--debug]                   - Export conversation by number")
    print("  python cgpt.py debug <number>                              - Show conversation structure details")
    print("  python cgpt.py search <term> [--content] [--export] [--n=X] [--debug] - Search for conversations")
    print("  python cgpt.py info                                        - Show information about the database")
    print("\nOptions:")
    print("  --content  : Search within message content (not just titles)")
    print("  --export   : Export the found conversation(s)")
    print("  --n=X      : Export the Xth conversation from search results (default: 1st)")
    print("  --debug    : Show detailed debug information")


def handle_list_command(history: List[Dict[str, Any]], args: List[str]) -> None:
    """
    Handle the 'list' command.
    
    Args:
        history: List of conversation dictionaries
        args: Command line arguments
    """
    count = 20
    if len(args) > 2 and args[2].isdigit():
        count = int(args[2])
    list_conversations(history, count)


def handle_export_command(history: List[Dict[str, Any]], args: List[str]) -> None:
    """
    Handle the 'export' command.
    
    Args:
        history: List of conversation dictionaries
        args: Command line arguments
    """
    if len(args) < 3:
        print("Error: Please provide a conversation number to export")
        return
    
    try:
        idx = int(args[2]) - 1  # Convert to 0-based index
        debug = "--debug" in args
        export_conversation(history, idx, debug)
    except ValueError:
        print("Error: Please provide a valid conversation number")


def handle_debug_command(history: List[Dict[str, Any]], args: List[str]) -> None:
    """
    Handle the 'debug' command.
    
    Args:
        history: List of conversation dictionaries
        args: Command line arguments
    """
    if len(args) < 3:
        print("Error: Please provide a conversation number to debug")
        return
    
    try:
        idx = int(args[2]) - 1  # Convert to 0-based index
        if idx < 0 or idx >= len(history):
            print(f"Error: Conversation number {idx+1} out of range (1-{len(history)})")
        else:
            convo = history[idx]
            print(f"Conversation: {convo.get('title', 'Untitled')}")
            analyze_conversation(convo)
    except ValueError:
        print("Error: Please provide a valid conversation number")


def handle_search_command(history: List[Dict[str, Any]], args: List[str]) -> None:
    """
    Handle the 'search' command.
    
    Args:
        history: List of conversation dictionaries
        args: Command line arguments
    """
    if len(args) < 3:
        print("Error: Please provide a search term")
        return
    
    term = args[2]
    search_content = "--content" in args
    should_export = "--export" in args
    debug = "--debug" in args
    
    # Perform search
    print(f"Searching {'content and titles' if search_content else 'titles'} for '{term}'...")
    results = search_conversations(history, term, search_content)
    
    if not results:
        print(f"No conversations found matching '{term}'")
        return
    
    # Display results
    display_search_results(results, term, search_content)
    
    # Handle export if requested
    if should_export:
        export_idx = 0  # Default to first result
        
        # Check for --n=X flag
        for arg in args:
            if arg.startswith("--n="):
                try:
                    export_idx = int(arg.split("=")[1]) - 1
                    if export_idx < 0 or export_idx >= len(results):
                        print(f"\nError: Index {export_idx+1} out of range (1-{len(results)})")
                        export_idx = 0
                except:
                    print(f"\nError: Invalid index format in {arg}")
                    export_idx = 0
                break
        
        # Export the selected result
        convo, context = get_search_result_by_index(results, export_idx + 1)
        if convo:
            print(f"\nExporting {'first' if export_idx == 0 else f'#{export_idx+1}'} matching conversation:")
            print("=" * 50)
            
            # Create a temporary history with just this conversation
            temp_history = [convo]
            export_conversation(temp_history, 0, debug)


def handle_info_command(history: List[Dict[str, Any]], args: List[str]) -> None:
    """
    Handle the 'info' command.
    
    Args:
        history: List of conversation dictionaries
        args: Command line arguments
    """
    print(f"Conversation database: {HISTORY_PATH}")
    print(f"Total conversations: {len(history)}")
    
    # Count messages from all formats
    total_msgs = 0
    for convo in history:
        # Direct messages list
        if 'messages' in convo and isinstance(convo['messages'], list):
            total_msgs += len(convo['messages'])
        # Mapping structure
        elif 'mapping' in convo and isinstance(convo['mapping'], dict):
            msg_count = 0
            for node_id, node in convo['mapping'].items():
                if 'message' in node and node['message']:
                    msg_count += 1
            total_msgs += msg_count
    
    print(f"Total messages: {total_msgs}")
    
    # Show sample structure of the first conversation
    if history:
        print("\nSample conversation structure:")
        analyze_conversation(history[0])


def parse_and_execute(args: Optional[List[str]] = None) -> None:
    """
    Parse command line arguments and execute the appropriate command.
    
    Args:
        args: Command line arguments (defaults to sys.argv)
    """
    if args is None:
        args = sys.argv
    
    # Load conversation history
    history = load_history(HISTORY_PATH)
    if not history:
        print(f"Error: No conversations found at {HISTORY_PATH}")
        print("Please check that the file exists and contains valid conversation data.")
        return
    
    if len(args) > 1:
        # Command-line argument mode
        command = args[1].lower()
        
        if command == "list":
            handle_list_command(history, args)
        elif command == "export":
            handle_export_command(history, args)
        elif command == "debug":
            handle_debug_command(history, args)
        elif command == "search":
            handle_search_command(history, args)
        elif command == "info":
            handle_info_command(history, args)
        else:
            print(f"Error: Unknown command '{command}'")
            show_usage()
    else:
        # No command provided - launch interactive mode
        launch_interactive_mode(history)


def launch_interactive_mode(history: List[Dict[str, Any]]) -> None:
    """
    Launch interactive mode (curses or simple fallback).
    
    Args:
        history: List of conversation dictionaries
    """
    try:
        # First try curses interface
        import curses
        from src.cli.cli_ui_interactive import HistoryOrganizer
        
        def main_curses(stdscr):
            organizer = HistoryOrganizer(stdscr, history)
            organizer.run()
        
        curses.wrapper(main_curses)
    except Exception as e:
        # Fall back to simple mode
        print(f"Error initializing curses: {e}")
        print("Falling back to simple mode...\n")
        try:
            from src.cli.cli_ui_interactive import simple_mode
            simple_mode(HISTORY_PATH)
        except Exception as e:
            # If simple mode fails, show usage
            print(f"Error in simple mode: {e}")
            print("\n")
            show_usage()


def get_conversation_count(history: List[Dict[str, Any]]) -> int:
    """
    Get the total number of conversations.
    
    Args:
        history: List of conversation dictionaries
        
    Returns:
        Total conversation count
    """
    return len(history)


def get_message_count(history: List[Dict[str, Any]]) -> int:
    """
    Get the total number of messages across all conversations.
    
    Args:
        history: List of conversation dictionaries
        
    Returns:
        Total message count
    """
    total_msgs = 0
    for convo in history:
        # Direct messages list
        if 'messages' in convo and isinstance(convo['messages'], list):
            total_msgs += len(convo['messages'])
        # Mapping structure
        elif 'mapping' in convo and isinstance(convo['mapping'], dict):
            msg_count = 0
            for node_id, node in convo['mapping'].items():
                if 'message' in node and node['message']:
                    msg_count += 1
            total_msgs += msg_count
    
    return total_msgs


def validate_conversation_index(index: int, history: List[Dict[str, Any]]) -> bool:
    """
    Validate that a conversation index is within valid range.
    
    Args:
        index: 1-based conversation index
        history: List of conversation dictionaries
        
    Returns:
        True if valid, False otherwise
    """
    return 1 <= index <= len(history)


if __name__ == '__main__':
    parse_and_execute()