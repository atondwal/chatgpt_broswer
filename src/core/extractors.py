#!/usr/bin/env python3
"""
Message extraction logic for ChatGPT conversation browser.

Handles extraction of messages from various ChatGPT conversation formats,
including complex nested structures and different export versions.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Set

from .models import Message, MessageRole


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