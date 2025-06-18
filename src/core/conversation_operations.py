#!/usr/bin/env python3
"""
Conversation operations for ChatGPT History Browser.

Contains classes for loading, searching, and exporting conversations.
"""

# Standard library imports
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Local imports
from .models import Conversation, Message, MessageRole
from .extractors import MessageExtractor


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