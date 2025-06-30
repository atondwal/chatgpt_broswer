#!/usr/bin/env python3
"""Loader for Gemini conversation history."""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid
from ccsm.core.models import Conversation, Message, MessageRole
from ccsm.core.logging_config import get_logger

logger = get_logger(__name__)


def load_gemini_conversations(file_path: str) -> List[Conversation]:
    """Load conversations from Gemini JSON format."""
    if os.path.isdir(file_path):
        # Load all conversations from a project directory
        conversations = []
        for session_dir in Path(file_path).iterdir():
            if session_dir.is_dir():
                # Look for checkpoint files within each session directory
                for checkpoint_file in session_dir.glob("checkpoint-*.json"):
                    conv = load_gemini_conversation(str(checkpoint_file))
                    if conv:
                        conversations.append(conv)
        return sorted(conversations, key=lambda c: c.create_time or 0, reverse=True)
    else:
        # Load single conversation file
        conv = load_gemini_conversation(file_path)
        return [conv] if conv else []


def load_gemini_conversation(file_path: str) -> Optional[Conversation]:
    """Load a single conversation from Gemini checkpoint-*.json file."""
    messages = []
    session_id = Path(file_path).parent.name # Session ID is the parent directory name
    first_timestamp = None
    last_timestamp = None

    try:
        file_stat = os.stat(file_path)
        file_modified_time = file_stat.st_mtime
    except (OSError, FileNotFoundError):
        file_modified_time = None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)
            for item in checkpoint_data:
                msg = parse_gemini_message(item)
                if msg:
                    messages.append(msg)
                # The checkpoint files don't seem to have a session ID or timestamp per message
                # We'll rely on file modification time and the first message's timestamp if available
                if 'timestamp' in item and first_timestamp is None:
                    ts = parse_timestamp(item['timestamp'])
                    if ts:
                        first_timestamp = ts

    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return None

    if not messages:
        return None

    conv_id = session_id
    title = generate_title(messages)
    metadata = {'source': 'gemini', 'file': file_path}

    return Conversation(
        id=conv_id,
        title=title,
        messages=messages,
        create_time=first_timestamp or file_modified_time,
        update_time=file_modified_time or last_timestamp,
        metadata=metadata
    )


def parse_gemini_message(data: Dict[str, Any]) -> Optional[Message]:
    """Parse a message from Gemini JSON format."""
    msg_type = data.get('role')
    if msg_type not in ['user', 'model']:
        return None

    role = MessageRole.USER if msg_type == 'user' else MessageRole.ASSISTANT
    
    content = ""
    if 'parts' in data and isinstance(data['parts'], list):
        content_parts = []
        for part in data['parts']:
            if 'text' in part:
                content_parts.append(part['text'])
        content = "\n".join(content_parts)
    elif 'message' in data:
        content = data['message']

    if not content:
        return None

    msg_id = str(uuid.uuid4()) # Generate a UUID for the message ID
    create_time = parse_timestamp(data.get('timestamp')) # Try to get timestamp from message data
    if create_time is None:
        create_time = datetime.now(timezone.utc).timestamp() # Fallback to current time

    return Message(
        id=msg_id,
        role=role,
        content=content,
        create_time=create_time,
        metadata=data
    )


def parse_timestamp(timestamp_str: str) -> Optional[float]:
    """Parse ISO timestamp to Unix timestamp."""
    if not timestamp_str:
        return None
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.timestamp()
    except (ValueError, AttributeError):
        return None


def generate_title(messages: List[Message]) -> str:
    """Generate a title for the conversation."""
    for msg in messages:
        if msg.role == MessageRole.USER and msg.content:
            title = msg.content.split('\n')[0]
            return title[:80] if len(title) > 80 else title
    
    if messages and messages[0].create_time:
        return f"Gemini session {datetime.fromtimestamp(messages[0].create_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M')}"

    return "Gemini conversation"
