#!/usr/bin/env python3
"""
Data loading and parsing module for the legacy CLI interface.

Handles all data loading, JSON parsing, and message extraction 
from different ChatGPT export formats.
"""

import json
from typing import Any, Dict, List, Optional, Set


def load_history(path: str) -> List[Dict[str, Any]]:
    """
    Load conversation history from a JSON file.
    
    Args:
        path: Path to the conversations.json file
        
    Returns:
        List of conversation dictionaries
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Check for expected format
            if isinstance(data, dict):
                return data.get('conversations', [])
            elif isinstance(data, list):
                return data
            else:
                print(f"Unexpected data format: {type(data)}")
                return []
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return []
    except Exception as e:
        print(f"Error loading history: {e}")
        return []


def get_message_content(msg: Dict[str, Any], debug: bool = False) -> str:
    """
    Extract content from a message in various formats.
    
    This function handles the complex task of extracting readable content
    from ChatGPT messages which can have various formats depending on
    the export method and ChatGPT version.
    
    Args:
        msg: Message dictionary
        debug: Enable debug output
        
    Returns:
        Extracted message content as string
    """
    if debug:
        print(f"Extracting content from message with keys: {', '.join(msg.keys()) if isinstance(msg, dict) else 'not a dict'}")
    
    # ChatGPT web client format
    if isinstance(msg, dict):
        # Strategy 1: Handle direct content field
        if 'content' in msg:
            content = msg.get('content', '')
            
            # String content
            if isinstance(content, str) and content:
                return content
                
            # Handle content that might be a list (for newer ChatGPT formats)
            elif isinstance(content, list):
                content_parts = []
                for part in content:
                    if isinstance(part, dict):
                        if 'text' in part:
                            content_parts.append(part['text'])
                        # Handle other types like images
                        elif 'type' in part and part['type'] == 'image_url':
                            content_parts.append(f"[IMAGE: {part.get('image_url', {}).get('url', 'Unknown image')}]")
                    elif isinstance(part, str):
                        content_parts.append(part)
                content = ' '.join(content_parts)
                if content:
                    return content
            
            # Handle content as a dictionary
            elif isinstance(content, dict):
                if 'parts' in content and isinstance(content['parts'], list):
                    return ' '.join([str(part) for part in content['parts'] if part])
                elif 'text' in content:
                    return content['text']
        
        # Strategy 2: Check for parts array directly in message
        if 'parts' in msg and isinstance(msg['parts'], list):
            parts_content = ' '.join([str(part) for part in msg['parts'] if part])
            if parts_content:
                return parts_content
        
        # Strategy 3: Handle content_type based messages
        if 'content_type' in msg:
            content_type = msg.get('content_type', '')
            
            # Text content
            if content_type == 'text' and 'parts' in msg:
                text_content = ' '.join([str(part) for part in msg['parts'] if part])
                if text_content:
                    return text_content
                
            # User instructions or context
            elif content_type in ['user_editable_context', 'user_instructions']:
                if 'user_profile' in msg:
                    return f"[USER PROFILE]\n{msg['user_profile']}"
                elif 'user_instructions' in msg:
                    return f"[USER INSTRUCTIONS]\n{msg['user_instructions']}"
            
            # Thoughts content type
            elif content_type == 'thoughts' and 'thoughts' in msg:
                thoughts = msg['thoughts']
                if isinstance(thoughts, list):
                    thought_parts = []
                    for thought in thoughts:
                        if isinstance(thought, dict):
                            if 'summary' in thought:
                                thought_parts.append(f"Summary: {thought['summary']}")
                            if 'content' in thought:
                                thought_parts.append(f"Content: {thought['content']}")
                    if thought_parts:
                        return "[THOUGHTS]\n" + "\n".join(thought_parts)
            
            # Reasoning recap
            elif content_type == 'reasoning_recap' and 'content' in msg:
                return f"[REASONING]\n{msg['content']}"
                
            # Code or other specialized content
            elif 'parts' in msg:
                try:
                    # Try to parse as JSON if it looks like it
                    if msg['parts'] and isinstance(msg['parts'][0], str) and msg['parts'][0].startswith('{') and msg['parts'][0].endswith('}'):
                        data = json.loads(msg['parts'][0])
                        if isinstance(data, dict):
                            if 'content' in data:
                                return data['content']
                            elif 'name' in data and 'type' in data and 'content' in data:
                                return f"[{data['type']}]\n{data['content']}"
                    
                    return ' '.join([str(part) for part in msg['parts'] if part])
                except Exception as e:
                    if debug:
                        print(f"Error parsing JSON: {e}")
                    return ' '.join([str(part) for part in msg['parts'] if part])
        
        # Strategy 4: Look for common patterns in different formats
        # Check for message key that might contain the actual message content
        if 'message' in msg and isinstance(msg['message'], dict):
            return get_message_content(msg['message'], debug)
        
        # Check for value key
        if 'value' in msg and msg['value']:
            return str(msg['value'])
            
        # Strategy 5: For debugging, dump any data as string
        if debug:
            try:
                return f"[DEBUG] {json.dumps(msg, indent=2)}"
            except:
                pass
    
    # Return indicator if nothing found
    return "[Empty or unsupported message format]"


def build_message_tree(mapping: Dict[str, Any], current_id: str, 
                      visited: Optional[Set[str]] = None, debug: bool = False) -> List[Dict[str, Any]]:
    """
    Recursively build a tree of messages from the mapping structure.
    
    Args:
        mapping: Mapping dictionary containing nodes
        current_id: Current node ID to process
        visited: Set of visited node IDs to prevent cycles
        debug: Enable debug output
        
    Returns:
        List of messages in tree order
    """
    if visited is None:
        visited = set()
    
    if not current_id or current_id in visited:
        return []
    
    visited.add(current_id)
    node = mapping.get(current_id, {})
    message = node.get('message', None)
    
    if debug:
        print(f"Processing node {current_id}")
        if message:
            print(f"  Has message with keys: {', '.join(message.keys())}")
    
    messages = []
    if message:
        messages.append(message)
    
    # Process all children
    for child_id in node.get('children', []):
        if child_id:
            child_messages = build_message_tree(mapping, child_id, visited, debug)
            messages.extend(child_messages)
    
    return messages


def extract_messages_from_mapping(mapping: Dict[str, Any], current_node: Optional[str] = None, 
                                debug: bool = False) -> List[Dict[str, Any]]:
    """
    Extract all messages from a mapping structure.
    
    Args:
        mapping: Mapping dictionary containing conversation tree
        current_node: Current node ID if available
        debug: Enable debug output
        
    Returns:
        List of extracted messages
    """
    if not mapping:
        return []
    
    # Strategy 1: If we have a current node, trace back to root and build tree
    if current_node and current_node in mapping:
        # Find the root by traversing parents
        root_id = current_node
        while mapping.get(root_id, {}).get('parent'):
            root_id = mapping.get(root_id, {}).get('parent')
        
        # Now build the message tree from the root
        messages = build_message_tree(mapping, root_id, None, debug)
        if messages:
            return messages
    
    # Strategy 2: Find all root nodes (no parent) and build trees
    messages = []
    for node_id, node in mapping.items():
        if not node.get('parent'):
            if debug:
                print(f"Found root node: {node_id}")
            # This is a root node - build tree from here
            tree_messages = build_message_tree(mapping, node_id, None, debug)
            messages.extend(tree_messages)
    
    # Strategy 3: If still no messages, just collect all messages in flat structure
    if not messages:
        if debug:
            print("Using fallback strategy: collecting all messages")
        for node_id, node in mapping.items():
            if 'message' in node and node['message']:
                messages.append(node['message'])
    
    # Sort by create time if available
    try:
        has_create_time = any(msg.get('create_time') for msg in messages)
        if has_create_time:
            messages.sort(key=lambda x: x.get('create_time', 0) or 0)
    except Exception as e:
        if debug:
            print(f"Warning: Could not sort messages by create_time: {e}")
    
    return messages


def analyze_conversation(convo: Dict[str, Any]) -> None:
    """
    Analyze conversation structure and print debug info.
    
    Args:
        convo: Conversation dictionary to analyze
    """
    print("\nDEBUG INFO:")
    print("-" * 50)
    
    print(f"Keys in conversation object: {', '.join(convo.keys())}")
    
    if 'messages' in convo:
        print(f"Number of messages: {len(convo['messages'])}")
        if convo['messages']:
            first_msg = convo['messages'][0]
            print(f"First message keys: {', '.join(first_msg.keys())}")
            if 'content' in first_msg:
                content = first_msg['content']
                print(f"Content type: {type(content)}")
                if isinstance(content, list):
                    print(f"Content list length: {len(content)}")
                    if content:
                        print(f"First content item type: {type(content[0])}")
                        if isinstance(content[0], dict):
                            print(f"First content item keys: {', '.join(content[0].keys())}")
    else:
        # Look for alternative message formats
        for key in convo.keys():
            if isinstance(convo[key], list) and len(convo[key]) > 0:
                first_item = convo[key][0]
                if isinstance(first_item, dict):
                    print(f"Possible message list in key '{key}': {len(convo[key])} items")
                    print(f"First item keys: {', '.join(first_item.keys())}")