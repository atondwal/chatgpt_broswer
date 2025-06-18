#!/usr/bin/env python3
"""
Search functionality module for the legacy CLI interface.

Provides both title-based and content-based conversation searching capabilities.
"""

from typing import Any, Dict, List, Tuple
from src.cli.cli_data_loader import get_message_content


def search_conversations_by_title(history: List[Dict[str, Any]], term: str) -> List[Tuple[Dict[str, Any], str]]:
    """
    Search conversations by title only (faster).
    
    Args:
        history: List of conversation dictionaries
        term: Search term (case insensitive)
        
    Returns:
        List of (conversation, match_context) tuples
    """
    term_lower = term.lower()
    return [(c, "title match") for c in history if term_lower in c.get('title', '').lower()]


def search_conversations_by_content(history: List[Dict[str, Any]], term: str, 
                                  context_length: int = 80) -> List[Tuple[Dict[str, Any], str]]:
    """
    Search conversations by content (slower but more thorough).
    
    Args:
        history: List of conversation dictionaries
        term: Search term (case insensitive)
        context_length: Length of context to show around matches
        
    Returns:
        List of (conversation, match_context) tuples
    """
    term_lower = term.lower()
    results = []
    
    for i, convo in enumerate(history):
        # Check title first
        if term_lower in convo.get('title', '').lower():
            results.append((convo, "title match"))
            continue
            
        # Then check message content
        found = False
        msgs = []
        
        # Handle different conversation formats
        if 'messages' in convo and isinstance(convo['messages'], list):
            msgs = convo['messages']
        elif 'mapping' in convo and isinstance(convo['mapping'], dict):
            for node_id, node in convo['mapping'].items():
                if 'message' in node and node['message']:
                    msgs.append(node['message'])
        
        # Search in message content
        matching_text = []
        for msg in msgs:
            try:
                content = get_message_content(msg)
                if term_lower in content.lower():
                    # Store a short context around the match
                    idx = content.lower().find(term_lower)
                    half_context = context_length // 2
                    start = max(0, idx - half_context)
                    end = min(len(content), idx + len(term) + half_context)
                    context = content[start:end]
                    if start > 0:
                        context = "..." + context
                    if end < len(content):
                        context = context + "..."
                    matching_text.append(context)
                    found = True
            except:
                continue
        
        if found:
            # First match with context
            context = matching_text[0] if matching_text else "content match"
            results.append((convo, context))
    
    return results


def search_conversations(history: List[Dict[str, Any]], term: str, 
                        search_content: bool = False, context_length: int = 80) -> List[Tuple[Dict[str, Any], str]]:
    """
    Search conversations with optional content search.
    
    Args:
        history: List of conversation dictionaries
        term: Search term (case insensitive)
        search_content: Whether to search in message content
        context_length: Length of context to show around matches
        
    Returns:
        List of (conversation, match_context) tuples
    """
    if search_content:
        return search_conversations_by_content(history, term, context_length)
    else:
        return search_conversations_by_title(history, term)


def display_search_results(results: List[Tuple[Dict[str, Any], str]], term: str, 
                          show_content: bool = False, max_results: int = 20) -> None:
    """
    Display search results in a formatted way.
    
    Args:
        results: List of (conversation, match_context) tuples
        term: Original search term
        show_content: Whether to show content context
        max_results: Maximum number of results to display
    """
    if not results:
        print(f"No conversations found matching '{term}'")
        return
    
    print(f"Found {len(results)} conversations matching '{term}':")
    print("=" * 50)
    
    for i, (convo, match_context) in enumerate(results[:max_results]):
        title = convo.get('title', f"Conversation {convo.get('id', i)}")
        
        if show_content and match_context != "title match":
            print(f"{i+1}. {title}")
            print(f"   Match: \"{match_context}\"")
        else:
            print(f"{i+1}. {title}")
    
    if len(results) > max_results:
        print(f"\n... and {len(results) - max_results} more results")


def get_search_result_by_index(results: List[Tuple[Dict[str, Any], str]], 
                              index: int) -> Tuple[Dict[str, Any], str, None]:
    """
    Get a search result by index (1-based).
    
    Args:
        results: List of search results
        index: 1-based index
        
    Returns:
        (conversation, match_context) tuple, or (None, None) if invalid index
    """
    if not results or index < 1 or index > len(results):
        return None, None
    
    return results[index - 1]


def extract_search_context(content: str, term: str, context_length: int = 80) -> str:
    """
    Extract context around a search term in content.
    
    Args:
        content: Content to search in
        term: Search term
        context_length: Total length of context to extract
        
    Returns:
        Context string with the search term highlighted
    """
    content_lower = content.lower()
    term_lower = term.lower()
    
    idx = content_lower.find(term_lower)
    if idx == -1:
        return ""
    
    half_context = context_length // 2
    start = max(0, idx - half_context)
    end = min(len(content), idx + len(term) + half_context)
    
    context = content[start:end]
    
    # Add ellipsis if we truncated
    if start > 0:
        context = "..." + context
    if end < len(content):
        context = context + "..."
    
    return context


def interactive_search_menu(history: List[Dict[str, Any]]) -> None:
    """
    Interactive search menu for finding conversations.
    
    Args:
        history: List of conversation dictionaries
    """
    while True:
        print("\n" + "=" * 50)
        print("CONVERSATION SEARCH")
        print("=" * 50)
        
        term = input("Enter search term (or 'q' to quit): ").strip()
        if not term or term.lower() == 'q':
            break
        
        print("\nSearch options:")
        print("1. Search titles only (fast)")
        print("2. Search titles and content (slow)")
        
        choice = input("Choose option (1 or 2, default 1): ").strip()
        search_content = choice == '2'
        
        print(f"\nSearching{'content and titles' if search_content else 'titles'}...")
        results = search_conversations(history, term, search_content)
        
        if not results:
            print(f"No conversations found matching '{term}'")
            continue
        
        display_search_results(results, term, search_content)
        
        while True:
            choice = input("\nEnter number to view conversation, 'n' for new search, 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                return
            elif choice.lower() == 'n':
                break
            elif choice.isdigit():
                idx = int(choice)
                convo, context = get_search_result_by_index(results, idx)
                if convo:
                    from src.cli.cli_ui_interactive import view_conversation
                    view_conversation(convo)
                else:
                    print(f"Invalid choice: {choice}")
            else:
                print(f"Invalid choice: {choice}")


def get_conversations_with_term_count(history: List[Dict[str, Any]], term: str) -> List[Tuple[Dict[str, Any], int]]:
    """
    Get conversations with count of how many times the term appears.
    
    Args:
        history: List of conversation dictionaries
        term: Search term
        
    Returns:
        List of (conversation, count) tuples sorted by count descending
    """
    term_lower = term.lower()
    results = []
    
    for convo in history:
        count = 0
        
        # Count in title
        title = convo.get('title', '').lower()
        count += title.count(term_lower)
        
        # Count in messages
        msgs = []
        if 'messages' in convo and isinstance(convo['messages'], list):
            msgs = convo['messages']
        elif 'mapping' in convo and isinstance(convo['mapping'], dict):
            for node_id, node in convo['mapping'].items():
                if 'message' in node and node['message']:
                    msgs.append(node['message'])
        
        for msg in msgs:
            try:
                content = get_message_content(msg).lower()
                count += content.count(term_lower)
            except:
                continue
        
        if count > 0:
            results.append((convo, count))
    
    # Sort by count descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results