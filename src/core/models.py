#!/usr/bin/env python3
"""
Core data models for ChatGPT conversation browser.

Defines the fundamental data structures used throughout the application.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


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