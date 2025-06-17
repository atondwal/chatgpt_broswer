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

import argparse
import curses
import json
import logging
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MessageRole(Enum):
    """Enumeration of possible message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    THOUGHTS = "thoughts"
    REASONING_RECAP = "reasoning_recap"
    USER_EDITABLE_CONTEXT = "user_editable_context"
    UNKNOWN = "unknown"


class ContentType(Enum):
    """Enumeration of possible content types."""
    TEXT = "text"
    THOUGHTS = "thoughts"
    REASONING_RECAP = "reasoning_recap"
    USER_EDITABLE_CONTEXT = "user_editable_context"
    CODE = "code"
    IMAGE = "image"
    UNKNOWN = "unknown"


@dataclass
class Message:
    """Represents a single message in a conversation."""
    id: str
    role: MessageRole
    content: str
    create_time: Optional[float] = None
    author: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate and normalize message data after initialization."""
        if isinstance(self.role, str):
            try:
                self.role = MessageRole(self.role)
            except ValueError:
                self.role = MessageRole.UNKNOWN


@dataclass
class Conversation:
    """Represents a complete conversation with metadata."""
    id: str
    title: str
    messages: List[Message]
    create_time: Optional[float] = None
    update_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

    @property
    def message_count(self) -> int:
        """Return the number of messages in this conversation."""
        return len(self.messages)

    @property
    def has_messages(self) -> bool:
        """Return True if the conversation has any messages."""
        return len(self.messages) > 0


class MessageExtractor:
    """Handles extraction of messages from various ChatGPT conversation formats."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def extract_messages_from_mapping(
        self,
        mapping: Dict[str, Any],
        current_node: Optional[str] = None
    ) -> List[Message]:
        """
        Extract messages from OpenAI's conversation mapping structure.
        
        Args:
            mapping: The conversation mapping dictionary
            current_node: Optional current node ID to start from
            
        Returns:
            List of extracted Message objects
        """
        if not mapping:
            return []

        try:
            # Strategy 1: Start from current node and find root
            if current_node and current_node in mapping:
                root_id = self._find_root_from_node(mapping, current_node)
                messages = self._build_message_tree(mapping, root_id)
                if messages:
                    return self._sort_messages(messages)

            # Strategy 2: Find all root nodes
            messages = []
            for node_id, node in mapping.items():
                if not node.get('parent'):
                    tree_messages = self._build_message_tree(mapping, node_id)
                    messages.extend(tree_messages)

            if messages:
                return self._sort_messages(messages)

            # Strategy 3: Fallback - collect all messages
            self.logger.warning("Using fallback message collection strategy")
            messages = []
            for node_id, node in mapping.items():
                if 'message' in node and node['message']:
                    message = self._parse_message(node['message'])
                    if message:
                        messages.append(message)

            return self._sort_messages(messages)

        except Exception as e:
            self.logger.error(f"Error extracting messages from mapping: {e}")
            if self.debug:
                raise
            return []

    def _find_root_from_node(self, mapping: Dict[str, Any], node_id: str) -> str:
        """Find the root node by traversing up from the given node."""
        current_id = node_id
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)
            node = mapping.get(current_id, {})
            parent = node.get('parent')
            if not parent:
                return current_id
            current_id = parent

        # If we hit a cycle or can't find root, return the original node
        return node_id

    def _build_message_tree(
        self,
        mapping: Dict[str, Any],
        root_id: str,
        visited: Optional[Set[str]] = None
    ) -> List[Message]:
        """
        Recursively build a message tree from the mapping structure.
        
        Args:
            mapping: The conversation mapping
            root_id: The root node ID to start from
            visited: Set of visited node IDs to prevent cycles
            
        Returns:
            List of Message objects in tree order
        """
        if visited is None:
            visited = set()

        if not root_id or root_id in visited:
            return []

        visited.add(root_id)
        node = mapping.get(root_id, {})
        
        messages = []
        
        # Add message from current node if it exists
        if 'message' in node and node['message']:
            message = self._parse_message(node['message'])
            if message:
                messages.append(message)

        # Recursively process children
        for child_id in node.get('children', []):
            if child_id:
                child_messages = self._build_message_tree(mapping, child_id, visited)
                messages.extend(child_messages)

        return messages

    def _parse_message(self, raw_message: Dict[str, Any]) -> Optional[Message]:
        """
        Parse a raw message dictionary into a Message object.
        
        Args:
            raw_message: Raw message data from ChatGPT export
            
        Returns:
            Parsed Message object or None if parsing fails
        """
        try:
            message_id = raw_message.get('id', '')
            role = self._extract_role(raw_message)
            content = self._extract_content(raw_message)
            create_time = raw_message.get('create_time')
            author = raw_message.get('author')
            metadata = {
                k: v for k, v in raw_message.items()
                if k not in ('id', 'role', 'content', 'create_time', 'author')
            }

            return Message(
                id=message_id,
                role=role,
                content=content,
                create_time=create_time,
                author=author,
                metadata=metadata
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse message: {e}")
            if self.debug:
                self.logger.debug(f"Raw message data: {raw_message}")
            return None

    def _extract_role(self, message: Dict[str, Any]) -> MessageRole:
        """Extract the role from a message."""
        # Try standard role field
        if 'role' in message:
            try:
                return MessageRole(message['role'])
            except ValueError:
                pass

        # Try content type as role
        content = message.get('content', {})
        if isinstance(content, dict) and 'content_type' in content:
            content_type = content['content_type']
            try:
                return MessageRole(content_type)
            except ValueError:
                pass

        # Try author role
        author = message.get('author', {})
        if isinstance(author, dict) and 'role' in author:
            try:
                return MessageRole(author['role'])
            except ValueError:
                pass

        # Try ID prefix
        message_id = message.get('id', '')
        if isinstance(message_id, str):
            if message_id.startswith('user-'):
                return MessageRole.USER
            elif message_id.startswith('assistant-'):
                return MessageRole.ASSISTANT
            elif message_id.startswith('system-'):
                return MessageRole.SYSTEM

        return MessageRole.UNKNOWN

    def _extract_content(self, message: Dict[str, Any]) -> str:
        """
        Extract content from a message in various formats.
        
        Args:
            message: Message dictionary
            
        Returns:
            Extracted content string
        """
        content = message.get('content', {})

        # Handle direct string content
        if isinstance(content, str):
            return content

        # Handle content dictionary
        if isinstance(content, dict):
            return self._extract_content_from_dict(content)

        # Handle content list
        if isinstance(content, list):
            return self._extract_content_from_list(content)

        # Check for parts directly in message
        if 'parts' in message and isinstance(message['parts'], list):
            return ' '.join(str(part) for part in message['parts'] if part)

        return "[Empty or unsupported message format]"

    def _extract_content_from_dict(self, content: Dict[str, Any]) -> str:
        """Extract content from a content dictionary."""
        content_type = content.get('content_type', '')

        # Handle text content
        if content_type == 'text' and 'parts' in content:
            parts = content['parts']
            if isinstance(parts, list):
                return ' '.join(str(part) for part in parts if part)

        # Handle thoughts content
        if content_type == 'thoughts' and 'thoughts' in content:
            thoughts = content['thoughts']
            if isinstance(thoughts, list):
                thought_parts = []
                for thought in thoughts:
                    if isinstance(thought, dict):
                        if 'summary' in thought:
                            thought_parts.append(f"Summary: {thought['summary']}")
                        if 'content' in thought:
                            thought_parts.append(f"Content: {thought['content']}")
                if thought_parts:
                    return "[THOUGHTS]\n" + "\n".join(thought_parts)

        # Handle reasoning recap
        if content_type == 'reasoning_recap' and 'content' in content:
            return f"[REASONING]\n{content['content']}"

        # Handle user context
        if content_type == 'user_editable_context':
            if 'user_profile' in content:
                return f"[USER PROFILE]\n{content['user_profile']}"
            if 'user_instructions' in content:
                return f"[USER INSTRUCTIONS]\n{content['user_instructions']}"

        # Handle parts in content
        if 'parts' in content and isinstance(content['parts'], list):
            parts_content = self._extract_content_from_parts(content['parts'])
            if parts_content:
                return parts_content

        # Handle text field
        if 'text' in content:
            return str(content['text'])

        return "[Empty or unsupported message format]"

    def _extract_content_from_list(self, content: List[Any]) -> str:
        """Extract content from a content list."""
        content_parts = []
        for part in content:
            if isinstance(part, dict):
                if 'text' in part:
                    content_parts.append(part['text'])
                elif 'type' in part and part['type'] == 'image_url':
                    url = part.get('image_url', {}).get('url', 'Unknown image')
                    content_parts.append(f"[IMAGE: {url}]")
            elif isinstance(part, str):
                content_parts.append(part)

        return ' '.join(content_parts) if content_parts else ""

    def _extract_content_from_parts(self, parts: List[Any]) -> str:
        """Extract content from a parts list, handling JSON content."""
        if not parts:
            return ""

        content_parts = []
        for part in parts:
            if not part:
                continue

            part_str = str(part)
            
            # Try to parse JSON content
            if part_str.startswith('{') and part_str.endswith('}'):
                try:
                    data = json.loads(part_str)
                    if isinstance(data, dict):
                        if 'content' in data:
                            content_parts.append(data['content'])
                        elif 'name' in data and 'type' in data and 'content' in data:
                            content_parts.append(f"[{data['type']}]\n{data['content']}")
                        else:
                            content_parts.append(part_str)
                    else:
                        content_parts.append(part_str)
                except json.JSONDecodeError:
                    content_parts.append(part_str)
            else:
                content_parts.append(part_str)

        return ' '.join(content_parts)

    def _sort_messages(self, messages: List[Message]) -> List[Message]:
        """Sort messages by create_time if available."""
        try:
            # Check if any messages have create_time
            has_create_time = any(msg.create_time for msg in messages)
            if has_create_time:
                return sorted(
                    messages,
                    key=lambda x: x.create_time or 0
                )
        except Exception as e:
            self.logger.warning(f"Failed to sort messages: {e}")

        return messages


class ConversationLoader:
    """Handles loading and parsing of ChatGPT conversation data."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.message_extractor = MessageExtractor(debug=debug)

    def load_conversations(self, file_path: Union[str, Path]) -> List[Conversation]:
        """
        Load conversations from a ChatGPT export file.
        
        Args:
            file_path: Path to the conversations JSON file
            
        Returns:
            List of parsed Conversation objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different export formats
            if isinstance(data, dict) and 'conversations' in data:
                raw_conversations = data['conversations']
            elif isinstance(data, list):
                raw_conversations = data
            else:
                self.logger.error(f"Unexpected data format: {type(data)}")
                return []

            conversations = []
            for raw_conv in raw_conversations:
                conversation = self._parse_conversation(raw_conv)
                if conversation:
                    conversations.append(conversation)

            self.logger.info(f"Loaded {len(conversations)} conversations")
            return conversations

        except FileNotFoundError:
            self.logger.error(f"Conversation file not found: {file_path}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in conversation file: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error loading conversations: {e}")
            if self.debug:
                raise
            return []

    def _parse_conversation(self, raw_conv: Dict[str, Any]) -> Optional[Conversation]:
        """
        Parse a raw conversation dictionary into a Conversation object.
        
        Args:
            raw_conv: Raw conversation data from export
            
        Returns:
            Parsed Conversation object or None if parsing fails
        """
        try:
            conv_id = raw_conv.get('id', raw_conv.get('conversation_id', ''))
            title = raw_conv.get('title', f'Conversation {conv_id}')
            create_time = raw_conv.get('create_time')
            update_time = raw_conv.get('update_time')

            # Extract messages
            messages = []
            if 'messages' in raw_conv and isinstance(raw_conv['messages'], list):
                # Direct messages format
                for raw_msg in raw_conv['messages']:
                    message = self.message_extractor._parse_message(raw_msg)
                    if message:
                        messages.append(message)
            elif 'mapping' in raw_conv and isinstance(raw_conv['mapping'], dict):
                # Mapping format
                current_node = raw_conv.get('current_node')
                messages = self.message_extractor.extract_messages_from_mapping(
                    raw_conv['mapping'], current_node
                )

            # Filter out empty messages
            messages = [msg for msg in messages if msg.content.strip() and 
                       msg.content != "[Empty or unsupported message format]"]

            metadata = {
                k: v for k, v in raw_conv.items()
                if k not in ('id', 'conversation_id', 'title', 'create_time', 'update_time', 'messages', 'mapping')
            }

            return Conversation(
                id=conv_id,
                title=title,
                messages=messages,
                create_time=create_time,
                update_time=update_time,
                metadata=metadata
            )

        except Exception as e:
            self.logger.warning(f"Failed to parse conversation: {e}")
            if self.debug:
                self.logger.debug(f"Raw conversation data: {raw_conv}")
            return None


class ConversationSearcher:
    """Handles searching through conversations."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def search_conversations(
        self,
        conversations: List[Conversation],
        search_term: str,
        search_content: bool = False
    ) -> List[Tuple[Conversation, str]]:
        """
        Search conversations by title and optionally content.
        
        Args:
            conversations: List of conversations to search
            search_term: Term to search for (case insensitive)
            search_content: Whether to search message content in addition to titles
            
        Returns:
            List of tuples: (conversation, match_context)
        """
        search_term = search_term.lower()
        results = []

        for conversation in conversations:
            # Check title first
            if search_term in conversation.title.lower():
                results.append((conversation, "title match"))
                continue

            # Check content if requested
            if search_content:
                match_context = self._search_conversation_content(conversation, search_term)
                if match_context:
                    results.append((conversation, match_context))

        self.logger.info(f"Found {len(results)} conversations matching '{search_term}'")
        return results

    def _search_conversation_content(self, conversation: Conversation, search_term: str) -> Optional[str]:
        """
        Search for a term within a conversation's message content.
        
        Args:
            conversation: Conversation to search
            search_term: Term to search for
            
        Returns:
            Context string around the match or None if not found
        """
        for message in conversation.messages:
            content_lower = message.content.lower()
            if search_term in content_lower:
                # Extract context around the match
                idx = content_lower.find(search_term)
                start = max(0, idx - 40)
                end = min(len(message.content), idx + len(search_term) + 40)
                context = message.content[start:end]
                
                if start > 0:
                    context = "..." + context
                if end < len(message.content):
                    context = context + "..."
                    
                return context

        return None


class ConversationExporter:
    """Handles exporting conversations to various formats."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def export_conversation_to_text(self, conversation: Conversation) -> str:
        """
        Export a conversation to plain text format.
        
        Args:
            conversation: Conversation to export
            
        Returns:
            Formatted text representation of the conversation
        """
        lines = [
            f"Conversation: {conversation.title}",
            "=" * 50
        ]

        if not conversation.has_messages:
            lines.append("\nNo messages found in this conversation.")
            return "\n".join(lines)

        for message in conversation.messages:
            lines.extend([
                f"\n{message.role.value.upper()}:",
                "-" * 50,
                message.content
            ])

        return "\n".join(lines)

    def print_conversation(self, conversation: Conversation) -> None:
        """Print a conversation to stdout."""
        print(self.export_conversation_to_text(conversation))


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
                import datetime
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
            from chatgpt_tui import ChatGPTTUI
            
            tui = ChatGPTTUI(
                conversations_path=str(self.conversations_path),
                debug=self.debug
            )
            tui.run()
        except ImportError:
            print("Error: TUI module not available. Make sure chatgpt_tui.py is in the same directory.")
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