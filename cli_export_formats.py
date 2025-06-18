#!/usr/bin/env python3
"""
Export and display formatting module for the legacy CLI interface.

Handles different export formats and conversation display logic.
"""

from typing import Any, Dict, List
from cli_data_loader import get_message_content, extract_messages_from_mapping, analyze_conversation


def export_conversation(history: List[Dict[str, Any]], idx: int = 0, debug: bool = False) -> None:
    """
    Export a single conversation to stdout.
    
    Args:
        history: List of conversation dictionaries
        idx: Index of conversation to export
        debug: Enable debug output
    """
    if not history or idx >= len(history):
        print("No conversation found at index", idx)
        return
    
    convo = history[idx]
    title = convo.get('title', 'Untitled Conversation')
    print(f"Conversation: {title}")
    print("=" * 50)
    
    if debug:
        analyze_conversation(convo)
    
    # Look for messages in multiple possible formats
    msgs = []
    if 'messages' in convo and isinstance(convo['messages'], list):
        msgs = convo['messages']
    elif 'mapping' in convo and isinstance(convo['mapping'], dict):
        # Handle OpenAI's alternate format
        try:
            mapping = convo['mapping']
            current_node_id = convo.get('current_node')
            
            # Use our improved message extraction function
            msgs = extract_messages_from_mapping(mapping, current_node_id, debug)
            
            if debug and msgs:
                print(f"Found {len(msgs)} messages using improved extraction")
                # Show first message details
                if msgs and len(msgs) > 0:
                    first_msg = msgs[0]
                    print(f"First message keys: {', '.join(first_msg.keys())}")
                    if 'content' in first_msg:
                        content_type = type(first_msg['content'])
                        print(f"Content type: {content_type}")
                        if isinstance(first_msg['content'], dict):
                            print(f"Content keys: {', '.join(first_msg['content'].keys())}")
        except Exception as e:
            print(f"Error parsing mapping format: {e}")
            if debug:
                import traceback
                traceback.print_exc()
    
    if not msgs:
        print("\nNo messages found in this conversation.")
        return
    
    for i, msg in enumerate(msgs):
        try:
            # Extract role, trying different known formats
            role = "unknown"
            
            # Standard format
            if msg.get('role'):
                role = msg.get('role')
            # Content type as role
            elif msg.get('content_type'):
                role = msg.get('content_type')
            # Author field
            elif msg.get('author'):
                if isinstance(msg['author'], dict) and 'role' in msg['author']:
                    role = msg['author']['role']
                else:
                    role = str(msg['author'])
            # Id field may contain role indicators
            elif msg.get('id') and isinstance(msg.get('id'), str):
                msg_id = msg.get('id')
                if msg_id.startswith('user-'):
                    role = 'user'
                elif msg_id.startswith('assistant-'):
                    role = 'assistant'
                elif msg_id.startswith('system-'):
                    role = 'system'
            # Message object inside may have role
            elif msg.get('message') and isinstance(msg['message'], dict) and msg['message'].get('role'):
                role = msg['message'].get('role')
            
            # Get content with debug flag if debugging
            content = get_message_content(msg, debug)
            
            if not content or content == "[Empty or unsupported message format]":
                # Skip empty messages
                if debug:
                    print(f"Skipping empty message: {msg.keys() if isinstance(msg, dict) else 'not a dict'}")
                continue
                
            print(f"\n{role.upper()}:")
            print("-" * 50)
            print(content)
        except Exception as e:
            print(f"\nError displaying message {i+1}: {str(e)}")
            if debug:
                import traceback
                traceback.print_exc()


def list_conversations(history: List[Dict[str, Any]], count: int = 20) -> None:
    """
    List available conversations.
    
    Args:
        history: List of conversation dictionaries
        count: Number of conversations to display
    """
    print(f"Found {len(history)} conversations")
    print("=" * 50)
    for i, convo in enumerate(history[:count]):
        title = convo.get('title', f"Conversation {convo.get('id', i)}")
        print(f"{i+1}. {title}")


def format_conversation_summary(convo: Dict[str, Any], index: int) -> str:
    """
    Format a single conversation for summary display.
    
    Args:
        convo: Conversation dictionary
        index: Display index
        
    Returns:
        Formatted summary string
    """
    title = convo.get('title', f"Conversation {convo.get('id', index)}")
    
    # Try to get message count
    msg_count = 0
    if 'messages' in convo and isinstance(convo['messages'], list):
        msg_count = len(convo['messages'])
    elif 'mapping' in convo and isinstance(convo['mapping'], dict):
        # Count messages in mapping
        msg_count = sum(1 for node in convo['mapping'].values() if node.get('message'))
    
    if msg_count > 0:
        return f"{index}. {title} ({msg_count} messages)"
    else:
        return f"{index}. {title}"


def export_conversation_to_file(history: List[Dict[str, Any]], idx: int, 
                               output_path: str, format_type: str = "text") -> bool:
    """
    Export a conversation to a file.
    
    Args:
        history: List of conversation dictionaries
        idx: Index of conversation to export
        output_path: Output file path
        format_type: Export format ('text', 'json', 'markdown')
        
    Returns:
        True if export successful, False otherwise
    """
    if not history or idx >= len(history):
        print(f"No conversation found at index {idx}")
        return False
    
    convo = history[idx]
    title = convo.get('title', 'Untitled Conversation')
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            if format_type == "json":
                import json
                json.dump(convo, f, indent=2, ensure_ascii=False)
            elif format_type == "markdown":
                f.write(f"# {title}\n\n")
                _export_conversation_markdown(convo, f)
            else:  # text format
                f.write(f"Conversation: {title}\n")
                f.write("=" * 50 + "\n")
                _export_conversation_text(convo, f)
        
        print(f"Exported conversation '{title}' to {output_path}")
        return True
        
    except Exception as e:
        print(f"Error exporting conversation: {e}")
        return False


def _export_conversation_text(convo: Dict[str, Any], file_handle) -> None:
    """Export conversation in plain text format."""
    # Extract messages using same logic as export_conversation
    msgs = []
    if 'messages' in convo and isinstance(convo['messages'], list):
        msgs = convo['messages']
    elif 'mapping' in convo and isinstance(convo['mapping'], dict):
        msgs = extract_messages_from_mapping(convo['mapping'], convo.get('current_node'))
    
    for i, msg in enumerate(msgs):
        try:
            # Extract role
            role = _extract_message_role(msg)
            content = get_message_content(msg)
            
            if content and content != "[Empty or unsupported message format]":
                file_handle.write(f"\n{role.upper()}:\n")
                file_handle.write("-" * 50 + "\n")
                file_handle.write(content + "\n")
        except Exception as e:
            file_handle.write(f"\nError displaying message {i+1}: {str(e)}\n")


def _export_conversation_markdown(convo: Dict[str, Any], file_handle) -> None:
    """Export conversation in markdown format."""
    # Extract messages using same logic as export_conversation
    msgs = []
    if 'messages' in convo and isinstance(convo['messages'], list):
        msgs = convo['messages']
    elif 'mapping' in convo and isinstance(convo['mapping'], dict):
        msgs = extract_messages_from_mapping(convo['mapping'], convo.get('current_node'))
    
    for i, msg in enumerate(msgs):
        try:
            role = _extract_message_role(msg)
            content = get_message_content(msg)
            
            if content and content != "[Empty or unsupported message format]":
                file_handle.write(f"\n## {role.title()}\n\n")
                file_handle.write(content + "\n\n")
        except Exception as e:
            file_handle.write(f"\n*Error displaying message {i+1}: {str(e)}*\n\n")


def _extract_message_role(msg: Dict[str, Any]) -> str:
    """Extract role from a message dictionary."""
    # Standard format
    if msg.get('role'):
        return msg.get('role')
    # Content type as role
    elif msg.get('content_type'):
        return msg.get('content_type')
    # Author field
    elif msg.get('author'):
        if isinstance(msg['author'], dict) and 'role' in msg['author']:
            return msg['author']['role']
        else:
            return str(msg['author'])
    # Id field may contain role indicators
    elif msg.get('id') and isinstance(msg.get('id'), str):
        msg_id = msg.get('id')
        if msg_id.startswith('user-'):
            return 'user'
        elif msg_id.startswith('assistant-'):
            return 'assistant'
        elif msg_id.startswith('system-'):
            return 'system'
    # Message object inside may have role
    elif msg.get('message') and isinstance(msg['message'], dict) and msg['message'].get('role'):
        return msg['message'].get('role')
    
    return "unknown"