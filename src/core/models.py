#!/usr/bin/env python3
"""
Core data models for ChatGPT conversation browser.

Defines the fundamental data structures used throughout the application.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from src.core.type_definitions import MessageDict, ConversationDict, Timestamp


class MessageRole(Enum):
    """Enumeration of possible message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
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

    def __post_init__(self) -> None:
        """Post-initialization processing for role validation."""
        if isinstance(self.role, str):
            try:
                self.role = MessageRole(self.role)
            except ValueError:
                self.role = MessageRole.UNKNOWN
    
    @classmethod
    def from_dict(cls, data: MessageDict) -> 'Message':
        """Create Message from dictionary data."""
        return cls(
            id=data['id'],
            role=MessageRole(data['role']),
            content=str(data['content']),  # Convert content to string
            create_time=data.get('create_time'),
            author=data.get('author'),
            metadata=data.get('metadata')
        )
    
    def to_dict(self) -> MessageDict:
        """Convert Message to dictionary."""
        result: MessageDict = {
            'id': self.id,
            'role': self.role.value,
            'content': self.content
        }
        
        if self.create_time is not None:
            result['create_time'] = self.create_time
        if self.author is not None:
            result['author'] = self.author
        if self.metadata is not None:
            result['metadata'] = self.metadata
            
        return result


@dataclass
class Conversation:
    """Represents a complete conversation with metadata."""
    id: str
    title: str
    messages: List[Message]
    create_time: Optional[Timestamp] = None
    update_time: Optional[Timestamp] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_dict(cls, data: ConversationDict) -> 'Conversation':
        """Create Conversation from dictionary data."""
        messages = [Message.from_dict(msg) for msg in data['messages']]
        
        return cls(
            id=data['id'],
            title=data['title'],
            messages=messages,
            create_time=data.get('create_time'),
            update_time=data.get('update_time'),
            metadata=data.get('metadata')
        )
    
    def to_dict(self) -> ConversationDict:
        """Convert Conversation to dictionary."""
        result: ConversationDict = {
            'id': self.id,
            'title': self.title,
            'messages': [msg.to_dict() for msg in self.messages],
            'create_time': self.create_time,
            'update_time': self.update_time
        }
        
        if self.metadata is not None:
            result['metadata'] = self.metadata
            
        return result
    
    def get_message_count(self) -> int:
        """Get the number of messages in this conversation."""
        return len(self.messages)
    
    def get_last_message_time(self) -> Optional[Timestamp]:
        """Get the timestamp of the last message."""
        if not self.messages:
            return None
        
        last_msg = self.messages[-1]
        return last_msg.create_time or self.update_time
    
    def has_user_messages(self) -> bool:
        """Check if conversation contains user messages."""
        return any(msg.role == MessageRole.USER for msg in self.messages)
    
    def has_assistant_messages(self) -> bool:
        """Check if conversation contains assistant messages."""
        return any(msg.role == MessageRole.ASSISTANT for msg in self.messages)