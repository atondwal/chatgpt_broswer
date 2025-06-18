#!/usr/bin/env python3
"""
ChatGPT History Browser

A high-quality tool for browsing, searching, and exporting ChatGPT conversation history.
Supports OpenAI's conversation export format with advanced search and display capabilities.

Usage:
    python chatgpt_browser.py list [count]
    python chatgpt_browser.py export <number> [--debug]
    python chatgpt_browser.py search <term> [--content] [--export] [--n=X] [--debug]
    python chatgpt_browser.py info

Author: Generated with Claude Code
"""

# Standard library imports
import datetime
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Import all classes from the modular structure
from .models import MessageRole, ContentType, Message, Conversation
from .extractors import MessageExtractor
from .conversation_operations import ConversationLoader, ConversationSearcher, ConversationExporter


# Backward compatibility - maintain the old function signatures for tests
def load_history(path: str) -> List[Dict[str, Any]]:
    """Legacy function for backward compatibility with tests."""
    loader = ConversationLoader()
    conversations = loader.load_conversations(path)
    # Convert back to raw format for compatibility
    return [
        {
            'id': conv.id,
            'title': conv.title,
            'messages': [
                {
                    'id': msg.id,
                    'role': msg.role.value,
                    'content': msg.content,
                    'create_time': msg.create_time,
                    'author': msg.author
                }
                for msg in conv.messages
            ],
            'create_time': conv.create_time,
            'update_time': conv.update_time
        }
        for conv in conversations
    ]


def get_message_content(message: Dict[str, Any], debug: bool = False) -> str:
    """Legacy function for backward compatibility with tests."""
    extractor = MessageExtractor(debug=debug)
    return extractor._extract_content(message)


def extract_messages_from_mapping(
    mapping: Dict[str, Any],
    current_node: Optional[str] = None,
    debug: bool = False
) -> List[Dict[str, Any]]:
    """Legacy function for backward compatibility with tests."""
    extractor = MessageExtractor(debug=debug)
    messages = extractor.extract_messages_from_mapping(mapping, current_node)
    # Convert back to raw format for compatibility
    return [
        {
            'id': msg.id,
            'role': msg.role.value,
            'content': msg.content,
            'create_time': msg.create_time,
            'author': msg.author
        }
        for msg in messages
    ]


def build_message_tree(
    mapping: Dict[str, Any],
    root_id: str,
    visited: Optional[Set[str]] = None,
    debug: bool = False
) -> List[Dict[str, Any]]:
    """Legacy function for backward compatibility with tests."""
    extractor = MessageExtractor(debug=debug)
    messages = extractor._build_message_tree(mapping, root_id, visited)
    # Convert back to raw format for compatibility
    return [
        {
            'id': msg.id,
            'role': msg.role.value,
            'content': msg.content,
            'create_time': msg.create_time,
            'author': msg.author
        }
        for msg in messages
    ]


def export_conversation(history: List[Dict[str, Any]], idx: int = 0, debug: bool = False) -> None:
    """Legacy function for backward compatibility with tests."""
    if not history or idx >= len(history):
        print("No conversation found at index", idx)
        return

    # Convert to new format
    raw_conv = history[idx]
    loader = ConversationLoader(debug=debug)
    conversation = loader._parse_conversation(raw_conv)
    
    if conversation:
        exporter = ConversationExporter(debug=debug)
        exporter.print_conversation(conversation)
    else:
        print("Failed to parse conversation")


def list_conversations(history: List[Dict[str, Any]], count: int = 20) -> None:
    """Legacy function for backward compatibility with tests."""
    print(f"Found {len(history)} conversations")
    print("=" * 50)
    for i, conv in enumerate(history[:count]):
        title = conv.get('title', f"Conversation {conv.get('id', i)}")
        print(f"{i+1}. {title}")


def main() -> int:
    """Main entry point for the application."""
    # Import here to avoid circular imports
    from ..cli.chatgpt_cli import ChatGPTBrowserCLI
    
    cli = ChatGPTBrowserCLI()
    return cli.run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())