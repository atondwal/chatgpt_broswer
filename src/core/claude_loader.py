#!/usr/bin/env python3
"""Claude conversation loader."""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from src.core.models import Conversation, Message, MessageRole


def parse_claude_message(claude_msg: Dict[str, Any], msg_id: str) -> Message:
    """Parse a Claude message into our Message format."""
    role_str = claude_msg.get("role", "user")
    
    # Map role to our enum
    if role_str == "assistant":
        role = MessageRole.ASSISTANT
    elif role_str == "system":
        role = MessageRole.SYSTEM
    else:
        role = MessageRole.USER
    
    # Extract content - handle different formats
    content = claude_msg.get("content", "")
    if isinstance(content, dict):
        if "text" in content:
            content = content["text"]
        elif "parts" in content:
            content = " ".join(content["parts"])
        else:
            content = str(content)
    elif content is None or content == "":
        content = "[Empty message]"
    else:
        content = str(content)
    
    return Message(msg_id, role, content)


def load_claude_conversations(file_path: str) -> List[Conversation]:
    """Load Claude conversations from JSONL file."""
    conversations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    # Skip malformed JSON lines
                    continue
                
                # Extract conversation data
                conv_id = data.get("id", f"conv_{line_num}")
                title = data.get("name", f"Conversation {line_num}")
                
                # Parse create time
                create_time = None
                created_at = data.get("created_at")
                if created_at:
                    try:
                        # Parse ISO format: "2024-01-01T10:00:00Z"
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        create_time = int(dt.timestamp())
                    except (ValueError, AttributeError):
                        create_time = None
                
                # Parse messages
                messages = []
                claude_messages = data.get("messages", [])
                for i, claude_msg in enumerate(claude_messages):
                    msg_id = f"{conv_id}_msg_{i}"
                    message = parse_claude_message(claude_msg, msg_id)
                    messages.append(message)
                
                conversation = Conversation(conv_id, title, messages, create_time)
                conversations.append(conversation)
    
    except FileNotFoundError:
        pass
    except Exception:
        # Handle other errors gracefully
        pass
    
    return conversations


def list_claude_projects() -> List[Dict[str, Any]]:
    """List all Claude projects in ~/.claude/projects/."""
    projects = []
    claude_dir = Path.home() / ".claude" / "projects"
    
    if not claude_dir.exists():
        return projects
    
    try:
        for project_dir in claude_dir.iterdir():
            if not project_dir.is_dir():
                continue
            
            # Look for JSONL conversation files
            conversation_files = list(project_dir.glob("*.jsonl"))
            conversation_count = 0
            last_modified = None
            
            for conv_file in conversation_files:
                try:
                    # Count lines in file for conversation count
                    with open(conv_file, 'r', encoding='utf-8') as f:
                        conversation_count += sum(1 for line in f if line.strip())
                    
                    # Get last modified time
                    mtime = conv_file.stat().st_mtime
                    if last_modified is None or mtime > last_modified:
                        last_modified = mtime
                        
                except Exception:
                    continue
            
            projects.append({
                "name": project_dir.name,
                "path": str(project_dir),
                "conversation_count": conversation_count,
                "last_modified": last_modified
            })
    
    except Exception:
        pass
    
    return projects