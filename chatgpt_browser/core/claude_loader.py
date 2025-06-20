#!/usr/bin/env python3
"""Loader for Claude Code conversation history."""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from chatgpt_browser.core.models import Conversation, Message, MessageRole
from chatgpt_browser.core.logging_config import get_logger

logger = get_logger(__name__)


def load_claude_conversations(file_path: str) -> List[Conversation]:
    """Load conversations from Claude JSONL format."""
    if os.path.isdir(file_path):
        # Load all conversations from a project directory
        conversations = []
        for jsonl_file in Path(file_path).glob("*.jsonl"):
            conv = load_claude_conversation(str(jsonl_file))
            if conv:
                conversations.append(conv)
        return sorted(conversations, key=lambda c: c.create_time or 0, reverse=True)
    else:
        # Load single conversation file
        conv = load_claude_conversation(file_path)
        return [conv] if conv else []


def load_claude_conversation(file_path: str) -> Optional[Conversation]:
    """Load a single conversation from Claude JSONL file."""
    messages = []
    session_id = None
    first_timestamp = None
    last_timestamp = None
    project_name = None
    
    # Get file modification time
    try:
        file_stat = os.stat(file_path)
        file_modified_time = file_stat.st_mtime
    except (OSError, FileNotFoundError):
        file_modified_time = None
    
    # Extract project name from path
    path_parts = Path(file_path).parts
    if ".claude" in path_parts and "projects" in path_parts:
        idx = path_parts.index("projects")
        if idx + 1 < len(path_parts):
            project_name = path_parts[idx + 1]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                    
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                # Extract session info - use the most recent sessionId found
                if 'sessionId' in data:
                    session_id = data['sessionId']
                
                # Track timestamps
                if 'timestamp' in data:
                    ts = parse_timestamp(data['timestamp'])
                    if ts:
                        if first_timestamp is None:
                            first_timestamp = ts
                        last_timestamp = ts
                
                # Extract message
                msg = parse_claude_message(data)
                if msg:
                    messages.append(msg)
    
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return None
    
    if not messages:
        return None
    
    # Use filename as session ID - this is what claude --resume expects
    filename_session_id = Path(file_path).stem
    conv_id = filename_session_id
    
    # Generate title from first user message or project info
    title = generate_title(messages, project_name)
    
    metadata = {'source': 'claude', 'file': file_path}
    if project_name:
        metadata['project'] = project_name
    
    return Conversation(
        id=conv_id,
        title=title,
        messages=messages,
        create_time=first_timestamp,
        update_time=file_modified_time or last_timestamp,
        metadata=metadata
    )


def parse_claude_message(data: Dict[str, Any]) -> Optional[Message]:
    """Parse a message from Claude JSONL format."""
    msg_type = data.get('type')
    
    if msg_type not in ['user', 'assistant']:
        return None
    
    message_data = data.get('message', {})
    if not message_data:
        return None
    
    # Extract role
    role = MessageRole.USER if msg_type == 'user' else MessageRole.ASSISTANT
    
    # Extract content
    content = extract_claude_content(message_data)
    if not content:
        return None
    
    # Generate ID from UUID or timestamp
    msg_id = data.get('uuid', str(data.get('timestamp', '')))
    
    # Parse timestamp
    create_time = parse_timestamp(data.get('timestamp'))
    
    return Message(
        id=msg_id,
        role=role,
        content=content,
        create_time=create_time,
        metadata=data
    )


def extract_claude_content(message_data: Dict[str, Any], for_title: bool = False) -> str:
    """Extract content from Claude message format."""
    content_list = message_data.get('content', [])
    
    if not isinstance(content_list, list):
        return ""
    
    parts = []
    for item in content_list:
        if isinstance(item, dict):
            item_type = item.get('type')
            
            if item_type == 'text':
                text = item.get('text', '')
                if text:
                    # For title generation, only use actual text content
                    if for_title:
                        # Skip tool results and system messages
                        skip_prefixes = (
                            '1. Replaced', 'File "', 'Applied ', 'The file ', 'Contents of',
                            'Error:', 'Traceback', 'WARNING:', 'INFO:', 'DEBUG:',
                            'Successfully', 'Failed to', 'Created', 'Updated', 'Deleted',
                            'Running', 'Executing', 'Processing', 'Building',
                            '```', '---', '===', '...', 'Note:'
                        )
                        if not text.startswith(skip_prefixes) and not text.strip().startswith(('#', '//', '/*')):
                            parts.append(text)
                    else:
                        parts.append(text)
            elif item_type == 'tool_use' and not for_title:
                # Format tool use as special content
                tool_name = item.get('name', 'unknown')
                tool_input = item.get('input', {})
                parts.append(f"[Tool: {tool_name}]")
                if isinstance(tool_input, dict) and tool_input:
                    # Show key tool inputs
                    for key, value in list(tool_input.items())[:3]:
                        parts.append(f"  {key}: {str(value)[:100]}")
            elif item_type == 'tool_result' and not for_title:
                # Show tool results
                content = item.get('content', '')
                if isinstance(content, str):
                    # Truncate long results
                    if len(content) > 200:
                        content = content[:200] + "..."
                    parts.append(f"[Tool Result: {content}]")
    
    return '\n'.join(parts) if parts else "[Empty message]"


def parse_timestamp(timestamp_str: str) -> Optional[float]:
    """Parse ISO timestamp to Unix timestamp."""
    if not timestamp_str:
        return None
    
    try:
        # Parse ISO format with timezone
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.timestamp()
    except (ValueError, AttributeError):
        return None


def generate_title(messages: List[Message], project_name: Optional[str]) -> str:
    """Generate a title for the conversation."""
    # Look through messages for a good title
    skip_continuation = True
    for i, msg in enumerate(messages):
        if msg.role == MessageRole.USER:
            # Get the original message data to extract cleaner content
            if hasattr(msg, 'metadata') and msg.metadata:
                message_data = msg.metadata.get('message', {})
                if message_data:
                    content = extract_claude_content(message_data, for_title=True)
                    
                    # Check if this is a continuation message
                    if "being continued from a previous conversation" in content:
                        # Extract the summary part after the analysis
                        if "Summary:" in content:
                            # Look for actual user messages in the summary
                            summary_start = content.find("Summary:")
                            if summary_start != -1:
                                summary_content = content[summary_start:]
                                # Look for quoted user messages
                                import re
                                user_quotes = re.findall(r'"([^"]+)"', summary_content)
                                for quote in user_quotes:
                                    if len(quote) > 20 and not quote.startswith("This session"):
                                        if len(quote) > 80:
                                            return quote[:77] + "..."
                                        return quote
                        continue
                    
                    # Use first substantial line
                    lines = content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if len(line) > 20 and not line.startswith('['):
                            # Truncate to reasonable length
                            if len(line) > 80:
                                return line[:77] + "..."
                            return line
    
    # If we only found continuation messages, try to extract something from them
    for msg in messages[:5]:  # Check first 5 messages
        if msg.role == MessageRole.ASSISTANT:
            content = msg.content
            # Look for descriptive phrases in assistant responses
            if "I'll help" in content or "Let me" in content or "I can" in content:
                lines = content.split('\n')
                for line in lines:
                    if any(phrase in line for phrase in ["I'll help", "Let me", "I can"]):
                        # Extract the action being performed
                        if len(line) > 20:
                            if len(line) > 80:
                                return line[:77] + "..."
                            return line
    
    # Fallback to project name or timestamp
    if project_name:
        # Clean up project name (remove leading hyphens)
        clean_name = project_name.lstrip('-').replace('-', '/')
        return f"Session in {clean_name}"
    
    if messages and messages[0].create_time:
        return f"Claude session {datetime.fromtimestamp(messages[0].create_time).strftime('%Y-%m-%d %H:%M')}"
    
    return "Claude conversation"


def encode_path_like_claude(path: Path) -> str:
    """Encode a path the same way Claude does for project directories."""
    # Claude encodes paths by replacing special characters with dashes and adding a leading -
    # e.g., /home/user/my_project -> -home-user-my-project
    # e.g., /home/user/project with spaces -> -home-user-project-with-spaces
    path_str = str(path)
    if path_str.startswith('/'):
        path_str = path_str[1:]  # Remove leading slash
    
    # Replace filesystem-problematic characters with dashes
    # This includes: / _ space . , ; : ! @ # $ % ^ & * ( ) + = [ ] { } | \ ` ~ ? < > "
    import re
    # Replace any sequence of non-alphanumeric, non-hyphen characters with a single dash
    path_str = re.sub(r'[^a-zA-Z0-9-]+', '-', path_str)
    # Clean up multiple consecutive dashes
    path_str = re.sub(r'-+', '-', path_str)
    # Remove trailing dashes
    path_str = path_str.strip('-')
    
    return '-' + path_str


def find_claude_project_for_cwd() -> Optional[str]:
    """Find the Claude project that contains the current working directory."""
    cwd = Path.cwd().resolve()
    projects_dir = Path.home() / ".claude" / "projects"
    
    if not projects_dir.exists():
        return None
    
    # Get all existing project names
    existing_projects = {p.name for p in projects_dir.iterdir() if p.is_dir()}
    
    # Find the deepest matching parent directory
    # Start with cwd and work up the directory tree
    current_path = cwd
    best_match = None
    
    while current_path != current_path.parent:
        encoded_path = encode_path_like_claude(current_path)
        if encoded_path in existing_projects:
            best_match = str(projects_dir / encoded_path)
            break
        current_path = current_path.parent
    
    return best_match


def list_claude_projects() -> List[Dict[str, Any]]:
    """List all Claude projects with metadata."""
    projects_dir = Path.home() / ".claude" / "projects"
    
    if not projects_dir.exists():
        return []
    
    projects = []
    for project_dir in projects_dir.iterdir():
        if project_dir.is_dir():
            # Count conversations
            jsonl_files = list(project_dir.glob("*.jsonl"))
            
            # Get most recent conversation time
            latest_time = None
            for jsonl_file in jsonl_files:
                try:
                    mtime = jsonl_file.stat().st_mtime
                    if latest_time is None or mtime > latest_time:
                        latest_time = mtime
                except (OSError, FileNotFoundError):
                    pass  # Skip files that can't be accessed
            
            projects.append({
                'name': project_dir.name,
                'path': str(project_dir),
                'conversation_count': len(jsonl_files),
                'last_modified': latest_time
            })
    
    # Sort by last modified
    return sorted(projects, key=lambda p: p.get('last_modified', 0), reverse=True)