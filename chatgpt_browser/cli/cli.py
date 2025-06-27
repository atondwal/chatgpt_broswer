#!/usr/bin/env python3
"""Simple command-line interface for ChatGPT History Browser."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from chatgpt_browser.core.loader import load_conversations
from chatgpt_browser.core.claude_loader import list_claude_projects, find_claude_project_for_cwd
from chatgpt_browser.core.time_utils import format_relative_time
from chatgpt_browser.core.exporter import export_conversation as export_conv
from chatgpt_browser.core.logging_config import setup_logging, get_logger
from chatgpt_browser.core.validation import validate_project_selection, validate_conversation_number, validate_file_path


def list_conversations(file_path: str, count: int = 20, format: str = "auto") -> None:
    """List recent conversations in claude --resume style."""
    conversations = load_conversations(file_path, format=format)
    
    if not conversations:
        print("No conversations found.")
        return
    
    # Print header
    print(f"     {'Modified':<12} {'Created':<12} {'# Messages':<11} Summary")
    
    # List conversations
    for i, conv in enumerate(conversations[:count]):
        # Format times
        modified = format_relative_time(conv.update_time)
        created = format_relative_time(conv.create_time)
        
        # Count messages
        msg_count = len(conv.messages)
        
        # Format the line
        # Use ❯ for first item, space for others
        marker = "❯" if i == 0 else " "
        
        # Truncate title if needed
        title = conv.title
        if len(title) > 50:
            title = title[:47] + "..."
        
        print(f"{marker} {i+1:2}. {modified:<12} {created:<12} {msg_count:>10} {title}")


def export_conversation(file_path: str, number: int, format: str = "auto", export_format: str = "text") -> None:
    """Export a conversation to stdout."""
    conversations = load_conversations(file_path, format=format)
    
    if not conversations:
        print("No conversations found.")
        return
        
    # Validate conversation number
    validated_num = validate_conversation_number(str(number), len(conversations))
    if validated_num is None:
        print(f"Error: Conversation {number} not found (1-{len(conversations)})")
        return
    
    idx = validated_num - 1
        
    conv = conversations[idx]
    
    # Export using shared exporter
    output = export_conv(conv, format=export_format)
    print(output)


def search_conversations(file_path: str, query: str, content: bool = False, format: str = "auto") -> None:
    """Search conversations by title or content."""
    conversations = load_conversations(file_path, format=format)
    query_lower = query.lower()
    
    results = []
    for i, conv in enumerate(conversations):
        # Check title
        if query_lower in conv.title.lower():
            results.append((i, conv, "title"))
            continue
            
        # Check content if requested
        if content:
            for msg in conv.messages:
                if query_lower in msg.content.lower():
                    results.append((i, conv, "content"))
                    break
    
    # Show results
    print(f"Found {len(results)} matches for '{query}'")
    print("=" * 50)
    
    for i, (idx, conv, match_type) in enumerate(results[:20]):
        print(f"{i+1}. [{idx+1}] {conv.title} ({match_type} match)")


def list_claude_projects_cmd() -> None:
    """List all Claude projects."""
    projects = list_claude_projects()
    
    if not projects:
        print("No Claude projects found in ~/.claude/projects/")
        return
    
    print(f"Found {len(projects)} Claude projects:")
    print("=" * 70)
    
    # Print header
    print(f"     {'Last Modified':<15} {'# Convos':<10} Project Name")
    
    for i, project in enumerate(projects, 1):
        name = project['name']
        count = project['conversation_count']
        
        # Format last modified time
        last_mod = format_relative_time(project['last_modified'])
        
        # Clean up project name and add leading slash
        if name.startswith('-'):
            clean_name = '/' + name[1:].replace('-', '/')
        else:
            clean_name = '/' + name.replace('-', '/')
        
        # Use ❯ for first item
        marker = "❯" if i == 1 else " "
        
        print(f"{marker} {i:2}. {last_mod:<15} {count:>8}  {clean_name}")
    
    print("\nUse: cgpt ~/.claude/projects/<PROJECT_NAME> list")
    print("  or: cgpt --claude-project <PROJECT_NAME> list")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Browse ChatGPT and Claude conversation history",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Add debug option
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    # File argument
    parser.add_argument(
        "conversations_file",
        nargs="?",
        help="Path to conversations file (JSON/JSONL) or Claude project directory"
    )
    
    # Format option
    parser.add_argument(
        "--format",
        choices=["auto", "chatgpt", "claude", "gemini"],
        default="auto",
        help="Conversation format (auto-detected by default)"
    )
    
    # Claude project option
    parser.add_argument(
        "--claude-project",
        help="Browse a specific Claude project by name"
    )

    # Gemini session option
    parser.add_argument(
        "--gemini",
        action="store_true",
        help="Browse Gemini sessions from ~/.gemini/tmp"
    )
    
    # Commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Projects command (for Claude)
    projects_parser = subparsers.add_parser("projects", help="List Claude projects")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List conversations")
    list_parser.add_argument("-n", "--count", type=int, default=20, help="Number to show")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export a conversation")
    export_parser.add_argument("number", type=int, help="Conversation number")
    export_parser.add_argument("--export-format", choices=["text", "markdown", "json"], 
                              default="text", help="Export format (default: text)")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search conversations")
    search_parser.add_argument("query", help="Search term")
    search_parser.add_argument("-c", "--content", action="store_true", 
                              help="Search in message content too")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(debug_mode=args.debug)
    logger = get_logger(__name__)
    
    # Handle Claude project shortcut
    if args.claude_project:
        args.conversations_file = str(Path.home() / ".claude" / "projects" / args.claude_project)
        args.format = "claude"

    # Handle Gemini session shortcut
    if args.gemini:
        args.conversations_file = str(Path.home() / ".gemini" / "tmp")
        args.format = "gemini"
    
    # Handle projects command
    if args.command == "projects":
        list_claude_projects_cmd()
        return
    
    # Auto-detect Claude project if no file specified
    if not args.conversations_file:
        # Check if we're in a Claude project directory
        claude_project = find_claude_project_for_cwd()
        if claude_project:
            args.conversations_file = claude_project
            args.format = "claude"
        else:
            # Fall back to showing Claude project picker with prompt
            projects = list_claude_projects()
            if not projects:
                print("No Claude projects found.")
                print("Please provide a conversation file path or create a Claude project.")
                sys.exit(1)
            
            list_claude_projects_cmd()
            print()
            try:
                choice = input("Enter project number or full path: ").strip()
                selection = validate_project_selection(choice, projects)
                
                if selection is None:
                    print(f"Invalid selection. Please enter a number (1-{len(projects)}) or a valid file path.")
                    sys.exit(1)
                elif isinstance(selection, int):
                    # Project number selected
                    args.conversations_file = projects[selection]['path']
                    args.format = "claude"
                else:
                    # File path selected
                    args.conversations_file = selection
            except (KeyboardInterrupt, EOFError):
                print("\nCancelled.")
                sys.exit(0)
    
    # Validate file path
    validated_path = validate_file_path(args.conversations_file, must_exist=True)
    if validated_path is None:
        print(f"Error: File not found or invalid: {args.conversations_file}")
        sys.exit(1)
    
    # Update with normalized path
    args.conversations_file = str(validated_path)
    
    # Execute command
    if args.command == "list":
        list_conversations(args.conversations_file, args.count, format=args.format)
    elif args.command == "export":
        export_conversation(args.conversations_file, args.number, format=args.format, 
                          export_format=args.export_format)
    elif args.command == "search":
        search_conversations(args.conversations_file, args.query, args.content, format=args.format)
    else:
        # Default to list
        list_conversations(args.conversations_file, format=args.format)


if __name__ == "__main__":
    main()