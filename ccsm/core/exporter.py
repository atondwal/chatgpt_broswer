#!/usr/bin/env python3
"""Shared conversation export functionality."""

import json
import io
import hashlib
from typing import Optional, Dict, Tuple, List, Any
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


def fold_json_entry(entry: Dict[str, Any], fold_lines: int = 50) -> Dict[str, Any]:
    """Return a copy of entry with large fields folded for readability.

    Args:
        entry: Raw JSON entry from JSONL
        fold_lines: Max lines before folding

    Returns:
        Copy of entry with large fields collapsed
    """
    import copy
    result = copy.deepcopy(entry)

    # Fold usage block to summary
    if 'message' in result and isinstance(result['message'], dict):
        msg = result['message']
        if 'usage' in msg and isinstance(msg['usage'], dict):
            usage = msg['usage']
            total = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
            msg['usage'] = {'_summary': f'{total} tokens', '_folded': True}

    # Fold toolUseResult stdout/stderr
    if 'toolUseResult' in result and isinstance(result['toolUseResult'], dict):
        tr = result['toolUseResult']
        for key in ['stdout', 'stderr']:
            if key in tr and isinstance(tr[key], str):
                lines = tr[key].split('\n')
                if len(lines) > fold_lines:
                    folded = lines[:5] + [f'... ({len(lines) - 10} lines folded) ...'] + lines[-5:]
                    tr[key] = '\n'.join(folded)

    # Fold large tool_result content in message.content
    if 'message' in result and isinstance(result['message'], dict):
        content_list = result['message'].get('content', [])
        if isinstance(content_list, list):
            for item in content_list:
                if isinstance(item, dict) and item.get('type') == 'tool_result':
                    content = item.get('content', '')
                    if isinstance(content, str):
                        lines = content.split('\n')
                        if len(lines) > fold_lines:
                            folded = lines[:5] + [f'... ({len(lines) - 10} lines folded) ...'] + lines[-5:]
                            item['content'] = '\n'.join(folded)

    return result


def export_aligned(
    raw_entries: List[Dict[str, Any]],
    fold_lines: int = 50
) -> Tuple[str, str]:
    """Generate aligned JSON and plaintext from raw JSONL entries.

    Args:
        raw_entries: List of raw JSON dicts from JSONL
        fold_lines: Max lines before folding tool output

    Returns:
        Tuple of (json_content, txt_content) with matching line counts per entry
    """
    from ccsm.core.claude_loader import render_message_detailed

    json_sections = []
    txt_sections = []
    separator = "═" * 71

    for entry in raw_entries:
        # Render JSON (folded, pretty-printed)
        folded = fold_json_entry(entry, fold_lines)
        json_str = json.dumps(folded, indent=2, ensure_ascii=False)
        json_lines = json_str.split('\n')

        # Render plaintext
        txt_str = render_message_detailed(entry, fold_lines)
        if not txt_str:
            continue
        txt_lines = [separator] + txt_str.split('\n')

        # Pad to equal height
        max_height = max(len(json_lines), len(txt_lines))
        while len(json_lines) < max_height:
            json_lines.append('')
        while len(txt_lines) < max_height:
            txt_lines.append('')

        json_sections.append('\n'.join(json_lines))
        txt_sections.append('\n'.join(txt_lines))

    return '\n'.join(json_sections) + '\n', '\n'.join(txt_sections) + '\n'