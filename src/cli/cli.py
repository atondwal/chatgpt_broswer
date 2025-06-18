#!/usr/bin/env python3
"""Simple command-line interface for ChatGPT History Browser."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from src.core.loader import load_conversations


def list_conversations(file_path: str, count: int = 20) -> None:
    """List recent conversations."""
    conversations = load_conversations(file_path)
    
    print(f"Found {len(conversations)} conversations")
    print("=" * 50)
    
    for i, conv in enumerate(conversations[:count]):
        print(f"{i+1}. {conv.title}")


def export_conversation(file_path: str, number: int) -> None:
    """Export a conversation to stdout."""
    conversations = load_conversations(file_path)
    
    if not conversations:
        print("No conversations found.")
        return
        
    idx = number - 1
    if idx < 0 or idx >= len(conversations):
        print(f"Error: Conversation {number} not found (1-{len(conversations)})")
        return
        
    conv = conversations[idx]
    
    # Print conversation
    print(f"Conversation: {conv.title}")
    print("=" * 50)
    
    for msg in conv.messages:
        print(f"\n{msg.role.value.upper()}:")
        print("-" * 50)
        print(msg.content)


def search_conversations(file_path: str, query: str, content: bool = False) -> None:
    """Search conversations by title or content."""
    conversations = load_conversations(file_path)
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


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Browse ChatGPT conversation history",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # File argument
    parser.add_argument(
        "conversations_file",
        nargs="?",
        default=str(Path.home() / ".chatgpt" / "conversations.json"),
        help="Path to conversations.json file"
    )
    
    # Commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List conversations")
    list_parser.add_argument("-n", "--count", type=int, default=20, help="Number to show")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export a conversation")
    export_parser.add_argument("number", type=int, help="Conversation number")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search conversations")
    search_parser.add_argument("query", help="Search term")
    search_parser.add_argument("-c", "--content", action="store_true", 
                              help="Search in message content too")
    
    args = parser.parse_args()
    
    # Check file exists
    if not Path(args.conversations_file).exists():
        print(f"Error: File not found: {args.conversations_file}")
        sys.exit(1)
    
    # Execute command
    if args.command == "list":
        list_conversations(args.conversations_file, args.count)
    elif args.command == "export":
        export_conversation(args.conversations_file, args.number)
    elif args.command == "search":
        search_conversations(args.conversations_file, args.query, args.content)
    else:
        # Default to list
        list_conversations(args.conversations_file)


if __name__ == "__main__":
    main()