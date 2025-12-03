#!/usr/bin/env python3
"""Type definitions for CCSM."""

from typing import TypedDict, List, Dict, Any, Optional, Union
from typing_extensions import NotRequired


class MessageDict(TypedDict):
    """ChatGPT message dictionary structure."""
    id: str
    role: str
    content: Union[str, Dict[str, Any]]
    create_time: NotRequired[Optional[float]]
    author: NotRequired[Optional[Dict[str, Any]]]
    metadata: NotRequired[Optional[Dict[str, Any]]]


class ConversationDict(TypedDict):
    """ChatGPT conversation dictionary structure."""
    id: str
    title: str
    create_time: Optional[float]
    update_time: Optional[float]
    messages: List[MessageDict]
    mapping: NotRequired[Optional[Dict[str, Any]]]
    moderation_results: NotRequired[Optional[List[Any]]]
    current_node: NotRequired[Optional[str]]


Timestamp = float
