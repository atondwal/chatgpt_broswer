#!/usr/bin/env python3
"""Shared conversation export functionality."""

import json
from typing import Optional
from src.core.models import Conversation, MessageRole


def export_conversation(conversation: Conversation, format: str = "markdown") -> str:
    """Export a conversation to the specified format.
    
    Args:
        conversation: The conversation to export
        format: Export format - "markdown", "text", or "json"
        
    Returns:
        Formatted conversation as string
    """
    if format == "json":
        return export_as_json(conversation)
    elif format == "text":
        return export_as_text(conversation)
    else:  # markdown is default
        return export_as_markdown(conversation)


def export_as_markdown(conversation: Conversation) -> str:
    """Export conversation as markdown."""
    lines = []
    
    # Title and metadata
    lines.append(f"# {conversation.title}")
    lines.append("")
    
    if conversation.create_time:
        from datetime import datetime
        created = datetime.fromtimestamp(conversation.create_time).strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"**Created:** {created}")
    
    if conversation.update_time and conversation.update_time != conversation.create_time:
        from datetime import datetime
        updated = datetime.fromtimestamp(conversation.update_time).strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"**Updated:** {updated}")
    
    lines.append(f"**Messages:** {len(conversation.messages)}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Messages
    for msg in conversation.messages:
        role_name = msg.role.value.upper()
        
        # Role header
        if msg.role == MessageRole.USER:
            lines.append(f"## 👤 {role_name}")
        elif msg.role == MessageRole.ASSISTANT:
            lines.append(f"## 🤖 {role_name}")
        else:
            lines.append(f"## {role_name}")
        
        lines.append("")
        
        # Content
        # Handle code blocks properly
        content = msg.content
        
        # If content has triple backticks, we need to be careful
        if "```" in content:
            # Already has code blocks, just add as-is
            lines.append(content)
        else:
            # Check if content looks like code (basic heuristic)
            code_indicators = ["import ", "def ", "class ", "function ", "const ", "var ", "let "]
            looks_like_code = any(indicator in content for indicator in code_indicators)
            
            if looks_like_code and "\n" in content:
                # Wrap in code block
                lines.append("```")
                lines.append(content)
                lines.append("```")
            else:
                lines.append(content)
        
        lines.append("")
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)


def export_as_text(conversation: Conversation) -> str:
    """Export conversation as plain text."""
    lines = []
    
    # Title
    lines.append(f"Conversation: {conversation.title}")
    lines.append("=" * 70)
    lines.append("")
    
    # Messages
    for msg in conversation.messages:
        role_name = msg.role.value.upper()
        lines.append(f"{role_name}:")
        lines.append("-" * 70)
        lines.append(msg.content)
        lines.append("")
    
    return "\n".join(lines)


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