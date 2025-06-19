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