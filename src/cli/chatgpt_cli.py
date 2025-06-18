#!/usr/bin/env python3
"""
Command-line interface for ChatGPT History Browser.

Provides comprehensive CLI commands for browsing, searching, and exporting conversations.
"""

# Standard library imports
import argparse
import datetime
import logging
import sys
from pathlib import Path
from typing import List, Optional

# Local imports
from src.core.conversation_operations import ConversationLoader, ConversationSearcher, ConversationExporter
from src.core.models import Conversation


class ChatGPTBrowserCLI:
    """Command-line interface for the ChatGPT history browser."""

    def __init__(self, conversations_path: Optional[str] = None, debug: bool = False):
        """
        Initialize the CLI.
        
        Args:
            conversations_path: Path to conversations JSON file
            debug: Enable debug logging
        """
        self.debug = debug
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Set default path
        if conversations_path:
            self.conversations_path = Path(conversations_path)
        else:
            self.conversations_path = Path.home() / '.chatgpt' / 'conversations.json'
        
        # Initialize components
        self.loader = ConversationLoader(debug=debug)
        self.searcher = ConversationSearcher(debug=debug)
        self.exporter = ConversationExporter(debug=debug)
        
        # Cache for loaded conversations
        self._conversations: Optional[List[Conversation]] = None

    def load_conversations(self) -> List[Conversation]:
        """Load conversations, using cache if available."""
        if self._conversations is None:
            self._conversations = self.loader.load_conversations(self.conversations_path)
        return self._conversations

    def cmd_list(self, count: int = 20) -> None:
        """List conversations command."""
        conversations = self.load_conversations()
        
        print(f"Found {len(conversations)} conversations")
        print("=" * 50)
        
        for i, conv in enumerate(conversations[:count]):
            print(f"{i+1}. {conv.title}")

    def cmd_export(self, conversation_number: int) -> None:
        """Export conversation command."""
        conversations = self.load_conversations()
        
        if not conversations:
            print("No conversations found.")
            return
            
        idx = conversation_number - 1  # Convert to 0-based
        if idx < 0 or idx >= len(conversations):
            print(f"Error: Conversation number {conversation_number} out of range (1-{len(conversations)})")
            return
            
        conversation = conversations[idx]
        self.exporter.print_conversation(conversation)

    def cmd_search(
        self,
        search_term: str,
        search_content: bool = False,
        export_index: Optional[int] = None
    ) -> None:
        """Search conversations command."""
        conversations = self.load_conversations()
        
        if search_content:
            print(f"Searching through conversation content for '{search_term}'...")
        
        results = self.searcher.search_conversations(
            conversations, search_term, search_content
        )
        
        if not results:
            print(f"No conversations found matching '{search_term}'")
            return
            
        print(f"Found {len(results)} conversations matching '{search_term}':")
        
        for i, (conversation, match_context) in enumerate(results[:20]):
            if search_content and match_context != "title match":
                print(f"{i+1}. {conversation.title}")
                print(f"   Match: \"{match_context}\"")
            else:
                print(f"{i+1}. {conversation.title}")
        
        # Export if requested
        if export_index is not None:
            idx = export_index - 1
            if 0 <= idx < len(results):
                print(f"\nExporting {'first' if idx == 0 else f'#{idx+1}'} matching conversation:")
                conversation = results[idx][0]
                self.exporter.print_conversation(conversation)
            else:
                print(f"\nError: Index {export_index} out of range (1-{len(results)})")

    def cmd_info(self) -> None:
        """Show information about the conversation database."""
        conversations = self.load_conversations()
        
        print(f"Conversation database: {self.conversations_path}")
        print(f"Total conversations: {len(conversations)}")
        
        total_messages = sum(conv.message_count for conv in conversations)
        print(f"Total messages: {total_messages}")
        
        if conversations:
            print("\nSample conversation structure:")
            sample_conv = conversations[0]
            print(f"ID: {sample_conv.id}")
            print(f"Title: {sample_conv.title}")
            print(f"Messages: {sample_conv.message_count}")
            if sample_conv.create_time:
                create_date = datetime.datetime.fromtimestamp(sample_conv.create_time)
                print(f"Created: {create_date}")

    def cmd_debug(self, conversation_number: int) -> None:
        """Debug conversation structure command."""
        conversations = self.load_conversations()
        
        if not conversations:
            print("No conversations found.")
            return
            
        idx = conversation_number - 1
        if idx < 0 or idx >= len(conversations):
            print(f"Error: Conversation number {conversation_number} out of range (1-{len(conversations)})")
            return
            
        conversation = conversations[idx]
        print(f"Conversation: {conversation.title}")
        print("\nDEBUG INFO:")
        print("-" * 50)
        print(f"ID: {conversation.id}")
        print(f"Message count: {conversation.message_count}")
        print(f"Create time: {conversation.create_time}")
        print(f"Update time: {conversation.update_time}")
        
        if conversation.metadata:
            print(f"Metadata keys: {', '.join(conversation.metadata.keys())}")
        
        if conversation.messages:
            first_msg = conversation.messages[0]
            print(f"\nFirst message:")
            print(f"  Role: {first_msg.role}")
            print(f"  Content length: {len(first_msg.content)}")
            print(f"  Content preview: {first_msg.content[:100]}...")

    def cmd_tui(self) -> None:
        """Launch the Terminal User Interface."""
        try:
            # Import here to avoid circular imports and make TUI optional
            from src.tui.enhanced_tui import ChatGPTTUI
            import curses
            
            tui = ChatGPTTUI(
                conversations_file=str(self.conversations_path),
                debug=self.debug
            )
            curses.wrapper(tui.run)
        except ImportError:
            print("Error: TUI module not available. Make sure enhanced_tui.py is available.")
        except Exception as e:
            if self.debug:
                raise
            print(f"Error launching TUI: {e}")

    def run(self, args: List[str]) -> int:
        """
        Run the CLI with the given arguments.
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success, 1 for error)
        """
        parser = self._create_parser()
        
        try:
            parsed_args = parser.parse_args(args)
            
            # Handle debug flag
            if hasattr(parsed_args, 'debug') and parsed_args.debug:
                self.debug = True
                logging.getLogger().setLevel(logging.DEBUG)
            
            # Route to appropriate command
            if parsed_args.command == 'list':
                self.cmd_list(parsed_args.count)
            elif parsed_args.command == 'export':
                self.cmd_export(parsed_args.number)
            elif parsed_args.command == 'search':
                export_index = None
                if parsed_args.export:
                    export_index = getattr(parsed_args, 'n', 1)
                self.cmd_search(
                    parsed_args.term,
                    parsed_args.content,
                    export_index
                )
            elif parsed_args.command == 'info':
                self.cmd_info()
            elif parsed_args.command == 'debug':
                self.cmd_debug(parsed_args.number)
            elif parsed_args.command == 'tui':
                self.cmd_tui()
            else:
                parser.print_help()
                return 1
                
            return 0
            
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            return 1
        except Exception as e:
            if self.debug:
                self.logger.exception("Unhandled exception")
                raise
            else:
                print(f"Error: {e}")
                return 1

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser."""
        parser = argparse.ArgumentParser(
            description="ChatGPT History Browser - Browse, search, and export ChatGPT conversations",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s tui                               # Launch interactive Terminal User Interface
  %(prog)s list 10                           # List first 10 conversations
  %(prog)s export 5 --debug                  # Export conversation #5 with debug info
  %(prog)s search "python" --content         # Search for "python" in content
  %(prog)s search "AI" --content --export --n=2  # Search and export 2nd result
  %(prog)s info                              # Show database information
            """
        )
        
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug output'
        )
        
        parser.add_argument(
            '--path',
            type=str,
            help='Path to conversations.json file (default: ~/.chatgpt/conversations.json)'
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # List command
        list_parser = subparsers.add_parser('list', help='List conversations')
        list_parser.add_argument(
            'count',
            type=int,
            nargs='?',
            default=20,
            help='Number of conversations to list (default: 20)'
        )
        
        # Export command
        export_parser = subparsers.add_parser('export', help='Export a conversation')
        export_parser.add_argument(
            'number',
            type=int,
            help='Conversation number to export'
        )
        
        # Search command
        search_parser = subparsers.add_parser('search', help='Search conversations')
        search_parser.add_argument(
            'term',
            help='Search term'
        )
        search_parser.add_argument(
            '--content',
            action='store_true',
            help='Search in message content (not just titles)'
        )
        search_parser.add_argument(
            '--export',
            action='store_true',
            help='Export the first matching conversation'
        )
        search_parser.add_argument(
            '--n',
            type=int,
            default=1,
            help='Export the Nth matching conversation (default: 1)'
        )
        
        # Info command
        subparsers.add_parser('info', help='Show database information')
        
        # Debug command
        debug_parser = subparsers.add_parser('debug', help='Debug conversation structure')
        debug_parser.add_argument(
            'number',
            type=int,
            help='Conversation number to debug'
        )
        
        # TUI command
        subparsers.add_parser('tui', help='Launch interactive Terminal User Interface')
        
        return parser


def main() -> int:
    """Main entry point for the application."""
    cli = ChatGPTBrowserCLI()
    return cli.run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())