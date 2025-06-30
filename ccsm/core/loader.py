#!/usr/bin/env python3
"""Simple conversation loader for ChatGPT exports."""

import json
import os
from typing import List, Dict, Any
from ccsm.core.models import Conversation, Message, MessageRole
from ccsm.core.claude_loader import load_claude_conversations, load_claude_conversation
from ccsm.core.gemini_loader import load_gemini_conversations, load_gemini_conversation
from ccsm.core.lazy_loader import LazyConversationLoader, ConversationMetadata
from ccsm.core.performance import get_performance_monitor, enable_performance_monitoring, ProgressIndicator
from ccsm.core.logging_config import get_logger

logger = get_logger(__name__)


def load_conversations(file_path: str, format: str = "auto", use_lazy_loading: bool = False) -> List[Conversation]:
    """Load conversations from file with format detection."""
    monitor = get_performance_monitor()
    
    with monitor.measure("load_conversations", file_path=file_path, format=format, lazy=use_lazy_loading):
        # Auto-detect format
        if format == "auto":
            if os.path.isdir(file_path):
                # Directory implies Claude or Gemini project
                if ".gemini" in file_path:
                    format = "gemini"
                else:
                    format = "claude"
            elif file_path.endswith('.jsonl'):
                format = "claude"
            else:
                format = "chatgpt"
        
        # Use lazy loading for large datasets
        if use_lazy_loading:
            return _load_conversations_lazy(file_path, format)
        
        # Route to appropriate loader
        if format == "claude":
            return load_claude_conversations(file_path)
        elif format == "gemini":
            return load_gemini_conversations(file_path)
        else:
            return load_chatgpt_conversations(file_path)


def load_chatgpt_conversations(file_path: str) -> List[Conversation]:
    """Load conversations from ChatGPT JSON export."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle wrapped format
    if isinstance(data, dict) and 'conversations' in data:
        data = data['conversations']
    
    conversations = []
    for conv_data in data:
        # Extract basic info
        conv_id = conv_data.get('id', '')
        title = conv_data.get('title', 'Untitled')
        create_time = conv_data.get('create_time')
        update_time = conv_data.get('update_time')
        
        # Extract messages
        messages = []
        mapping = conv_data.get('mapping', {})
        current_node = conv_data.get('current_node')
        
        if mapping:
            # Build message tree from mapping
            messages = extract_messages_from_mapping(mapping, current_node)
        elif 'messages' in conv_data:
            # Direct message list
            for msg_data in conv_data['messages']:
                msg = parse_message(msg_data)
                if msg:
                    messages.append(msg)
        
        if conv_id and messages:
            conversations.append(Conversation(
                id=conv_id,
                title=title,
                messages=messages,
                create_time=create_time,
                update_time=update_time,
                metadata=conv_data
            ))
    
    return conversations


def extract_messages_from_mapping(mapping: Dict[str, Any], current_node: str = None) -> List[Message]:
    """Extract messages from OpenAI's conversation mapping."""
    messages = []
    
    # Find root nodes
    roots = []
    for node_id, node in mapping.items():
        if not node.get('parent'):
            roots.append(node_id)
    
    # Build tree from each root
    for root_id in roots:
        add_messages_from_node(mapping, root_id, messages, set())
    
    # Sort by creation time if available
    messages.sort(key=lambda m: m.create_time or 0)
    return messages


def add_messages_from_node(mapping: Dict, node_id: str, messages: List[Message], visited: set):
    """Recursively add messages from a node and its children."""
    if not node_id or node_id in visited:
        return
    
    visited.add(node_id)
    node = mapping.get(node_id, {})
    
    # Add message from this node
    if 'message' in node and node['message']:
        msg = parse_message(node['message'])
        if msg:
            messages.append(msg)
    
    # Process children
    for child_id in node.get('children', []):
        add_messages_from_node(mapping, child_id, messages, visited)


def parse_message(msg_data: Dict[str, Any]) -> Message:
    """Parse a message from various formats."""
    if not msg_data:
        return None
    
    # Extract ID
    msg_id = msg_data.get('id', '')
    
    # Extract role
    role = MessageRole.UNKNOWN
    if 'role' in msg_data:
        try:
            role = MessageRole(msg_data['role'])
        except ValueError:
            pass
    elif 'author' in msg_data and isinstance(msg_data['author'], dict):
        author_role = msg_data['author'].get('role')
        if author_role:
            try:
                role = MessageRole(author_role)
            except ValueError:
                pass
    
    # Extract content
    content = extract_content(msg_data)
    
    if msg_id and content:
        return Message(
            id=msg_id,
            role=role,
            content=content,
            create_time=msg_data.get('create_time'),
            author=msg_data.get('author'),
            metadata=msg_data
        )
    
    return None


def extract_content(msg_data: Dict[str, Any]) -> str:
    """Extract content from various message formats."""
    content = msg_data.get('content', {})
    
    # Direct string
    if isinstance(content, str):
        return content
    
    # Content dict with parts
    if isinstance(content, dict):
        if 'parts' in content:
            parts = content['parts']
            if isinstance(parts, list):
                return ' '.join(str(p) for p in parts if p)
        elif 'text' in content:
            return content['text']
    
    # Content list
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and 'text' in item:
                parts.append(item['text'])
            elif isinstance(item, str):
                parts.append(item)
        return ' '.join(parts)
    
    # Fallback
    return str(content) if content else "[Empty message]"


def _load_conversations_lazy(file_path: str, format: str) -> List[Conversation]:
    """Load conversations using lazy loading system."""
    lazy_loader = LazyConversationLoader(cache_size=50, cache_memory_mb=100)
    
    # Register loaders
    lazy_loader.register_loader("chatgpt", _load_single_chatgpt_conversation)
    lazy_loader.register_loader("claude", load_claude_conversation)
    lazy_loader.register_loader("gemini", load_gemini_conversation)
    
    # Scan for metadata
    metadata_list = lazy_loader.scan_conversations(file_path, format)
    
    if not metadata_list:
        logger.warning(f"No conversations found in {file_path}")
        return []
    
    # Show progress for large datasets
    if len(metadata_list) > 50:
        progress = ProgressIndicator(len(metadata_list), "Loading conversations")
        
        conversations = []
        for i, metadata in enumerate(metadata_list):
            conv = lazy_loader.load_conversation(metadata.id)
            if conv:
                conversations.append(conv)
            progress.update()
        
        progress.finish()
        return conversations
    else:
        # Load all conversations for smaller datasets
        conversations = []
        for metadata in metadata_list:
            conv = lazy_loader.load_conversation(metadata.id)
            if conv:
                conversations.append(conv)
        return conversations


def _load_single_chatgpt_conversation(file_path: str) -> Conversation:
    """Load a single ChatGPT conversation from file."""
    conversations = load_chatgpt_conversations(file_path)
    return conversations[0] if conversations else None


def enable_performance_mode(enabled: bool = True) -> None:
    """Enable performance monitoring for conversation loading."""
    enable_performance_monitoring(enabled)
    

def get_loader_stats() -> Dict[str, Any]:
    """Get performance statistics for loader operations."""
    monitor = get_performance_monitor()
    return monitor.get_stats()

