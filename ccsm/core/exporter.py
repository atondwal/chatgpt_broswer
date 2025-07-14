#!/usr/bin/env python3
"""Shared conversation export functionality."""

import json
import io
import hashlib
from typing import Optional, Dict, Tuple
from datetime import datetime
from ccsm.core.models import Conversation, MessageRole

# Simple in-memory cache for exported conversations
_export_cache: Dict[str, Tuple[str, float]] = {}
_cache_max_size = 50


def export_conversation(conversation: Conversation, format: str = "markdown") -> str:
    """Export a conversation to the specified format.
    
    Args:
        conversation: The conversation to export
        format: Export format - "markdown", "text", or "json"
        
    Returns:
        Formatted conversation as string
    """
    # Create cache key from conversation ID, update time, and format
    cache_key = _get_cache_key(conversation, format)
    
    # Check cache first
    if cache_key in _export_cache:
        content, cached_time = _export_cache[cache_key]
        # Use cached version if conversation hasn't been updated
        if conversation.update_time and conversation.update_time <= cached_time:
            return content
    
    # Generate content
    if format == "json":
        content = export_as_json(conversation)
    elif format == "text":
        content = export_as_text(conversation)
    else:  # markdown is default
        content = export_as_markdown(conversation)
    
    # Cache the result
    _cache_export(cache_key, content)
    
    return content


def _get_cache_key(conversation: Conversation, format: str) -> str:
    """Generate cache key for conversation."""
    key_data = f"{conversation.id}:{conversation.update_time or 0}:{format}"
    return hashlib.md5(key_data.encode()).hexdigest()


def _cache_export(cache_key: str, content: str) -> None:
    """Cache exported content with LRU eviction."""
    global _export_cache
    
    # Simple LRU: remove oldest entries if cache is full
    if len(_export_cache) >= _cache_max_size:
        # Remove oldest entry
        oldest_key = min(_export_cache.keys(), 
                        key=lambda k: _export_cache[k][1])
        del _export_cache[oldest_key]
    
    _export_cache[cache_key] = (content, datetime.now().timestamp())


def export_as_markdown(conversation: Conversation) -> str:
    """Export conversation as markdown using optimized string building."""
    # Use StringIO for efficient string building
    output = io.StringIO()
    
    # Pre-format timestamps to avoid repeated formatting
    created_str = None
    updated_str = None
    if conversation.create_time:
        created_str = datetime.fromtimestamp(conversation.create_time).strftime("%Y-%m-%d %H:%M:%S")
    if conversation.update_time and conversation.update_time != conversation.create_time:
        updated_str = datetime.fromtimestamp(conversation.update_time).strftime("%Y-%m-%d %H:%M:%S")
    
    # Title and metadata
    output.write(f"# {conversation.title}\n\n")
    
    # Add session ID for resuming Claude sessions
    output.write(f"**Session ID:** {conversation.id}\n")
    
    if created_str:
        output.write(f"**Created:** {created_str}\n")
    if updated_str:
        output.write(f"**Updated:** {updated_str}\n")
    
    output.write(f"**Messages:** {len(conversation.messages)}\n\n---\n\n")
    
    # Pre-compile code detection patterns for efficiency
    code_indicators = ("import ", "def ", "class ", "function ", "const ", "var ", "let ")
    
    # Messages
    for msg in conversation.messages:
        role_name = msg.role.value.upper()
        
        # Role header
        if msg.role == MessageRole.USER:
            output.write(f"## 👤 {role_name}\n\n")
        elif msg.role == MessageRole.ASSISTANT:
            output.write(f"## 🤖 {role_name}\n\n")
        else:
            output.write(f"## {role_name}\n\n")
        
        # Content
        content = msg.content
        
        # Optimized code detection
        if "```" in content:
            # Already has code blocks
            output.write(content)
        else:
            # Quick check for code patterns
            looks_like_code = ("\n" in content and 
                             any(content.find(indicator) != -1 for indicator in code_indicators))
            
            if looks_like_code:
                output.write("```\n")
                output.write(content)
                output.write("\n```")
            else:
                output.write(content)
        
        output.write("\n\n---\n\n")
    
    return output.getvalue()


def export_as_text(conversation: Conversation) -> str:
    """Export conversation as plain text using optimized string building."""
    output = io.StringIO()
    
    # Title and session ID
    output.write(f"Conversation: {conversation.title}\n")
    output.write(f"Session ID: {conversation.id}\n")
    output.write("=" * 70)
    output.write("\n\n")
    
    # Messages
    separator = "-" * 70
    for msg in conversation.messages:
        role_name = msg.role.value.upper()
        output.write(f"{role_name}:\n")
        output.write(separator)
        output.write("\n")
        output.write(msg.content)
        output.write("\n\n")
    
    return output.getvalue()


def export_as_json(conversation: Conversation) -> str:
    """Export conversation as JSON."""
    data = {
        "id": conversation.id,
        "title": conversation.title,
        "create_time": conversation.create_time,
        "update_time": conversation.update_time,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role.value,
                "content": msg.content,
                "create_time": msg.create_time
            }
            for msg in conversation.messages
        ]
    }
    
    return json.dumps(data, indent=2, ensure_ascii=False)