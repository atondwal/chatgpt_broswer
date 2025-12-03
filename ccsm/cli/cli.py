#!/usr/bin/env python3
"""Simple command-line interface for ChatGPT History Browser."""

import argparse
import sys
from pathlib import Path
from typing import Optional

import json
import subprocess
import tempfile

from ccsm.core.loader import load_conversations
from ccsm.core.claude_loader import list_claude_projects, find_claude_project_for_cwd, load_raw_entries
from ccsm.core.time_utils import format_relative_time
from ccsm.core.exporter import export_conversation as export_conv, export_aligned
from ccsm.core.logging_config import setup_logging, get_logger
from ccsm.core.validation import validate_project_selection, validate_conversation_number, validate_file_path


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


def aligned_export(file_path: str, output_dir: str = ".", fold_lines: int = 50) -> None:
    """Generate aligned JSON and plaintext files from a JSONL session."""
    entries = load_raw_entries(file_path)
    if not entries:
        print(f"No entries found in {file_path}")
        return

    json_content, txt_content = export_aligned(entries, fold_lines)

    base_name = Path(file_path).stem
    output_path = Path(output_dir)

    json_file = output_path / f"{base_name}.json"
    txt_file = output_path / f"{base_name}.txt"

    json_file.write_text(json_content, encoding='utf-8')
    txt_file.write_text(txt_content, encoding='utf-8')

    print(f"Created: {json_file}")
    print(f"Created: {txt_file}")


def compact_json(file_path: str, output: Optional[str] = None) -> None:
    """Convert pretty JSON array back to JSONL format."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse as JSON array
    try:
        entries = json.loads(f'[{content}]'.replace('}\n{', '},\n{'))
    except json.JSONDecodeError:
        # Try parsing as newline-separated JSON objects
        entries = []
        for chunk in content.split('\n{'):
            chunk = chunk.strip()
            if not chunk:
                continue
            if not chunk.startswith('{'):
                chunk = '{' + chunk
            if chunk.endswith(','):
                chunk = chunk[:-1]
            try:
                entries.append(json.loads(chunk))
            except json.JSONDecodeError:
                continue

    if not entries:
        print(f"No valid JSON entries found in {file_path}")
        return

    # Determine output path
    if output is None:
        output = str(Path(file_path).with_suffix('.jsonl'))

    # Write as JSONL
    with open(output, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f"Wrote {len(entries)} entries to {output}")


def edit_session(file_path: str, fold_lines: int = 50, output: Optional[str] = None) -> None:
    """Open session in vim with aligned split view."""
    import uuid

    entries = load_raw_entries(file_path)
    if not entries:
        print(f"No entries found in {file_path}")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        json_content, txt_content = export_aligned(entries, fold_lines)

        base_name = Path(file_path).stem
        json_file = Path(tmpdir) / f"{base_name}.json"
        txt_file = Path(tmpdir) / f"{base_name}.txt"

        json_file.write_text(json_content, encoding='utf-8')
        txt_file.write_text(txt_content, encoding='utf-8')

        # Open in nvim with split view
        cmd = [
            'nvim', '-O', str(json_file), str(txt_file),
            '-c', 'windo set scrollbind | windo set cursorbind',
            '-c', 'windo set nomodified'
        ]

        try:
            subprocess.run(cmd)
        except FileNotFoundError:
            # Fall back to vim
            cmd[0] = 'vim'
            subprocess.run(cmd)

        # Check if JSON was modified
        new_content = json_file.read_text(encoding='utf-8')
        if new_content != json_content:
            # Determine output path
            if output:
                out_path = output
            else:
                # Generate new UUID for resumable edited session
                orig_path = Path(file_path)
                new_uuid = str(uuid.uuid4())
                out_path = str(orig_path.parent / f"{new_uuid}.jsonl")

            response = input(f"\nJSON was modified. Save to {out_path}? [Y/n] ").strip().lower()
            if response != 'n':
                compact_json(str(json_file), out_path)
                print(f"Saved edited session to: {out_path}")
                print(f"Resume with: claude --resume {Path(out_path).stem}")


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


def _handle_standalone_command(cmd: str, args: list) -> None:
    """Handle standalone commands that don't need conversations_file."""
    parser = argparse.ArgumentParser(prog=f"ccsm {cmd}")

    if cmd == "aligned":
        parser.add_argument("session_file", help="Path to JSONL session file")
        parser.add_argument("--output-dir", "-o", default=".", help="Output directory")
        parser.add_argument("--fold-lines", "-f", type=int, default=50,
                           help="Max lines before folding tool output")
        parsed = parser.parse_args(args)
        aligned_export(parsed.session_file, parsed.output_dir, parsed.fold_lines)

    elif cmd == "compact":
        parser.add_argument("json_file", help="Path to pretty JSON file")
        parser.add_argument("--output", "-o", help="Output JSONL file path")
        parsed = parser.parse_args(args)
        compact_json(parsed.json_file, parsed.output)

    elif cmd == "edit":
        parser.add_argument("session_file", help="Path to JSONL session file")
        parser.add_argument("--fold-lines", "-f", type=int, default=50,
                           help="Max lines before folding tool output")
        parser.add_argument("--output", "-o", help="Output file path")
        parsed = parser.parse_args(args)
        edit_session(parsed.session_file, parsed.fold_lines, parsed.output)


def main():
    """Main entry point."""
    # Handle standalone commands that don't use conversations_file
    standalone_commands = {'aligned', 'compact', 'edit'}
    if len(sys.argv) > 1 and sys.argv[1] in standalone_commands:
        _handle_standalone_command(sys.argv[1], sys.argv[2:])
        return

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

    # Aligned export command
    aligned_parser = subparsers.add_parser("aligned", help="Export aligned JSON + plaintext")
    aligned_parser.add_argument("session_file", help="Path to JSONL session file")
    aligned_parser.add_argument("--output-dir", "-o", default=".", help="Output directory")
    aligned_parser.add_argument("--fold-lines", "-f", type=int, default=50,
                               help="Max lines before folding tool output")

    # Compact command
    compact_parser = subparsers.add_parser("compact", help="Convert JSON back to JSONL")
    compact_parser.add_argument("json_file", help="Path to pretty JSON file")
    compact_parser.add_argument("--output", "-o", help="Output JSONL file path")

    # Edit command
    edit_parser = subparsers.add_parser("edit", help="Edit session in vim split view")
    edit_parser.add_argument("session_file", help="Path to JSONL session file")
    edit_parser.add_argument("--fold-lines", "-f", type=int, default=50,
                            help="Max lines before folding tool output")
    edit_parser.add_argument("--output", "-o", help="Output file path (default: <original>-edited-<timestamp>.jsonl)")

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

    # Handle aligned command (doesn't need conversation file validation)
    if args.command == "aligned":
        aligned_export(args.session_file, args.output_dir, args.fold_lines)
        return

    # Handle compact command
    if args.command == "compact":
        compact_json(args.json_file, args.output)
        return

    # Handle edit command
    if args.command == "edit":
        edit_session(args.session_file, args.fold_lines)
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