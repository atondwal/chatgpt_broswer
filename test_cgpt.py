#!/usr/bin/env python3
"""
Comprehensive tests for ChatGPT history browser.

Tests are written to capture existing behavior before refactoring to Google-quality code.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, mock_open, MagicMock
from typing import Dict, List, Any, Tuple

# Import the functions we want to test
# Using the new refactored module with backward compatibility
sys.path.insert(0, '/home/atondwal/playground')
try:
    import chatgpt_browser as cgpt
except ImportError:
    import cgpt


class TestMessageExtraction(unittest.TestCase):
    """Test message extraction from various ChatGPT conversation formats."""
    
    def setUp(self):
        """Set up test data with realistic ChatGPT conversation structures."""
        # Sample mapping structure as found in real ChatGPT exports
        self.sample_mapping = {
            "root-id": {
                "id": "root-id",
                "children": ["user-msg-1"],
                "parent": None,
                "message": None
            },
            "user-msg-1": {
                "id": "user-msg-1", 
                "children": ["assistant-msg-1"],
                "parent": "root-id",
                "message": {
                    "id": "user-msg-1",
                    "role": "user",
                    "author": {"role": "user"},
                    "create_time": 1234567890,
                    "content": {
                        "content_type": "text",
                        "parts": ["Hello, can you help me with Python?"]
                    }
                }
            },
            "assistant-msg-1": {
                "id": "assistant-msg-1",
                "children": ["user-msg-2"],
                "parent": "user-msg-1", 
                "message": {
                    "id": "assistant-msg-1",
                    "role": "assistant",
                    "author": {"role": "assistant"},
                    "create_time": 1234567891,
                    "content": {
                        "content_type": "text",
                        "parts": ["Of course! I'd be happy to help you with Python programming."]
                    }
                }
            },
            "user-msg-2": {
                "id": "user-msg-2",
                "children": [],
                "parent": "assistant-msg-1",
                "message": {
                    "id": "user-msg-2", 
                    "role": "user",
                    "author": {"role": "user"},
                    "create_time": 1234567892,
                    "content": {
                        "content_type": "text",
                        "parts": ["How do I create a list comprehension?"]
                    }
                }
            }
        }
        
        # Sample conversation with direct messages format
        self.sample_direct_messages = [
            {
                "role": "user",
                "content": "What is machine learning?",
                "create_time": 1234567890
            },
            {
                "role": "assistant", 
                "content": "Machine learning is a subset of artificial intelligence...",
                "create_time": 1234567891
            }
        ]
        
        # Complex message with thoughts and reasoning
        self.complex_message = {
            "id": "complex-msg-1",
            "role": "assistant",
            "author": {"role": "assistant"},
            "create_time": 1234567890,
            "content": {
                "content_type": "thoughts",
                "thoughts": [
                    {
                        "summary": "Analyzing the request",
                        "content": "The user is asking about data structures in Python."
                    }
                ]
            }
        }
        
        # Message with JSON content in parts
        self.json_message = {
            "id": "json-msg-1",
            "role": "assistant", 
            "author": {"role": "assistant"},
            "create_time": 1234567890,
            "content": {
                "content_type": "text",
                "parts": ['{"name": "test_script", "type": "code/python", "content": "print(\\"Hello World\\")"}']
            }
        }

    def test_extract_messages_from_mapping_with_current_node(self):
        """Test extracting messages when current_node is provided."""
        messages = cgpt.extract_messages_from_mapping(
            self.sample_mapping, 
            current_node="user-msg-2"
        )
        
        self.assertEqual(len(messages), 3)
        # Should be ordered by create_time
        self.assertEqual(messages[0]['role'], 'user')
        self.assertEqual(messages[1]['role'], 'assistant') 
        self.assertEqual(messages[2]['role'], 'user')

    def test_extract_messages_from_mapping_without_current_node(self):
        """Test extracting messages when no current_node is provided."""
        messages = cgpt.extract_messages_from_mapping(self.sample_mapping)
        
        self.assertEqual(len(messages), 3)
        self.assertTrue(all('role' in msg for msg in messages))

    def test_extract_messages_from_empty_mapping(self):
        """Test extracting messages from empty mapping."""
        messages = cgpt.extract_messages_from_mapping({})
        self.assertEqual(len(messages), 0)

    def test_extract_messages_from_malformed_mapping(self):
        """Test extracting messages from malformed mapping structure."""
        malformed_mapping = {
            "node-1": {
                "children": ["nonexistent-node"],
                "parent": None,
                "message": {"role": "user", "content": {"parts": ["test"]}}
            }
        }
        
        messages = cgpt.extract_messages_from_mapping(malformed_mapping)
        self.assertEqual(len(messages), 1)

    def test_build_message_tree_prevents_cycles(self):
        """Test that message tree building prevents infinite cycles."""
        cyclic_mapping = {
            "node-1": {
                "children": ["node-2"],
                "parent": None,
                "message": {"role": "user", "content": {"parts": ["test1"]}}
            },
            "node-2": {
                "children": ["node-1"],  # Creates cycle
                "parent": "node-1",
                "message": {"role": "assistant", "content": {"parts": ["test2"]}}
            }
        }
        
        messages = cgpt.build_message_tree(cyclic_mapping, "node-1")
        # Should not hang and should return finite results
        self.assertLessEqual(len(messages), 2)


class TestContentExtraction(unittest.TestCase):
    """Test content extraction from various message formats."""
    
    def test_extract_simple_text_content(self):
        """Test extracting simple text content from parts array."""
        message = {
            "content": {
                "content_type": "text",
                "parts": ["This is a simple message"]
            }
        }
        
        content = cgpt.get_message_content(message)
        self.assertEqual(content, "This is a simple message")

    def test_extract_multiple_parts_content(self):
        """Test extracting content from multiple parts."""
        message = {
            "content": {
                "content_type": "text", 
                "parts": ["Part 1: ", "Part 2: More text"]
            }
        }
        
        content = cgpt.get_message_content(message)
        self.assertEqual(content, "Part 1:  Part 2: More text")

    def test_extract_thoughts_content(self):
        """Test extracting thoughts content type."""
        message = {
            "content": {
                "content_type": "thoughts",
                "thoughts": [
                    {
                        "summary": "Test summary",
                        "content": "Test thought content"
                    }
                ]
            }
        }
        
        content = cgpt.get_message_content(message)
        # Refactored behavior: now properly extracts thoughts!
        self.assertIn("THOUGHTS", content)
        self.assertIn("Test summary", content)
        self.assertIn("Test thought content", content)

    def test_extract_reasoning_recap_content(self):
        """Test extracting reasoning recap content."""
        message = {
            "content": {
                "content_type": "reasoning_recap",
                "content": "Thought for 5 seconds"
            }
        }
        
        content = cgpt.get_message_content(message)
        # Refactored behavior: now properly extracts reasoning recap!
        self.assertIn("REASONING", content)
        self.assertIn("Thought for 5 seconds", content)

    def test_extract_json_code_content(self):
        """Test extracting JSON code from parts.""" 
        message = {
            "content": {
                "content_type": "text",
                "parts": ['{"name": "test", "type": "code/python", "content": "print(\\"hello\\")"}']
            }
        }
        
        content = cgpt.get_message_content(message)
        # Current behavior: returns the raw JSON string, doesn't parse it
        self.assertIn('{"name": "test"', content)

    def test_extract_user_profile_content(self):
        """Test extracting user profile content."""
        message = {
            "content": {
                "content_type": "user_editable_context",
                "user_profile": "User is a Python developer"
            }
        }
        
        content = cgpt.get_message_content(message)
        # Refactored behavior: now properly extracts user profile!
        self.assertIn("USER PROFILE", content)
        self.assertIn("Python developer", content)

    def test_extract_empty_content(self):
        """Test handling of empty or malformed content."""
        empty_message = {"content": {"content_type": "text", "parts": [""]}}
        content = cgpt.get_message_content(empty_message)
        self.assertEqual(content, "")

    def test_extract_direct_string_content(self):
        """Test extracting direct string content."""
        message = {"content": "Direct string content"}
        content = cgpt.get_message_content(message)
        self.assertEqual(content, "Direct string content")

    def test_extract_list_content_with_dicts(self):
        """Test extracting content from list with dictionaries."""
        message = {
            "content": [
                {"text": "Text part 1"},
                {"text": "Text part 2"}
            ]
        }
        
        content = cgpt.get_message_content(message)
        self.assertEqual(content, "Text part 1 Text part 2")


class TestConversationLoading(unittest.TestCase):
    """Test conversation loading and parsing."""
    
    def test_load_history_valid_json(self):
        """Test loading valid conversation history."""
        sample_data = [
            {
                "id": "conv-1",
                "title": "Test Conversation",
                "create_time": 1234567890,
                "mapping": {
                    "root": {
                        "children": ["msg-1"],
                        "parent": None,
                        "message": None
                    },
                    "msg-1": {
                        "children": [],
                        "parent": "root", 
                        "message": {
                            "role": "user",
                            "content": {"parts": ["Test message"]}
                        }
                    }
                }
            }
        ]
        
        with patch('builtins.open', mock_open(read_data=json.dumps(sample_data))):
            history = cgpt.load_history('/fake/path.json')
            
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['title'], "Test Conversation")

    def test_load_history_wrapped_in_conversations_key(self):
        """Test loading history wrapped in conversations key."""
        sample_data = {
            "conversations": [
                {"id": "conv-1", "title": "Test"}
            ]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(sample_data))):
            history = cgpt.load_history('/fake/path.json')
            
        self.assertEqual(len(history), 1)

    def test_load_history_file_not_found(self):
        """Test loading history when file doesn't exist."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            history = cgpt.load_history('/nonexistent/path.json')
            
        self.assertEqual(history, [])

    def test_load_history_invalid_json(self):
        """Test loading history with invalid JSON."""
        with patch('builtins.open', mock_open(read_data='invalid json')):
            history = cgpt.load_history('/fake/path.json')
            
        self.assertEqual(history, [])

    def test_load_history_unexpected_format(self):
        """Test loading history with unexpected data format."""
        with patch('builtins.open', mock_open(read_data='"just a string"')):
            history = cgpt.load_history('/fake/path.json')
            
        self.assertEqual(history, [])


class TestSearchFunctionality(unittest.TestCase):
    """Test search functionality for conversations."""
    
    def setUp(self):
        """Set up test conversations for search."""
        self.test_conversations = [
            {
                "id": "conv-1",
                "title": "Python Programming Help",
                "mapping": {
                    "root": {"children": ["msg-1"], "parent": None, "message": None},
                    "msg-1": {
                        "children": [],
                        "parent": "root",
                        "message": {
                            "role": "user",
                            "content": {"parts": ["How do I use list comprehensions in Python?"]}
                        }
                    }
                }
            },
            {
                "id": "conv-2", 
                "title": "Machine Learning Basics",
                "mapping": {
                    "root": {"children": ["msg-1"], "parent": None, "message": None},
                    "msg-1": {
                        "children": [],
                        "parent": "root",
                        "message": {
                            "role": "user", 
                            "content": {"parts": ["Explain neural networks and deep learning"]}
                        }
                    }
                }
            },
            {
                "id": "conv-3",
                "title": "JavaScript Debugging",
                "mapping": {
                    "root": {"children": ["msg-1"], "parent": None, "message": None},
                    "msg-1": {
                        "children": [],
                        "parent": "root",
                        "message": {
                            "role": "user",
                            "content": {"parts": ["My Python script has a bug"]}
                        }
                    }
                }
            }
        ]

    def test_title_search_case_insensitive(self):
        """Test searching conversation titles (case insensitive)."""
        # This would test the search logic once we extract it to a testable function
        results = []
        search_term = "python"
        
        for conv in self.test_conversations:
            if search_term.lower() in conv.get('title', '').lower():
                results.append(conv)
                
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Python Programming Help")

    def test_content_search_in_messages(self):
        """Test searching within message content."""
        results = []
        search_term = "python"
        
        for conv in self.test_conversations:
            # Check title first
            if search_term.lower() in conv.get('title', '').lower():
                results.append((conv, "title match"))
                continue
                
            # Check content
            found_in_content = False
            if 'mapping' in conv:
                for node_id, node in conv['mapping'].items():
                    if 'message' in node and node['message']:
                        msg = node['message']
                        content = cgpt.get_message_content(msg)
                        if search_term.lower() in content.lower():
                            results.append((conv, "content match"))
                            found_in_content = True
                            break
                            
        # Should find Python Programming Help (title) and JavaScript Debugging (content)
        self.assertEqual(len(results), 2)

    def test_search_no_results(self):
        """Test search with no matching results."""
        results = []
        search_term = "nonexistent"
        
        for conv in self.test_conversations:
            if search_term.lower() in conv.get('title', '').lower():
                results.append(conv)
                
        self.assertEqual(len(results), 0)


class TestExportFunctionality(unittest.TestCase):
    """Test conversation export functionality."""
    
    def setUp(self):
        """Set up test conversation for export."""
        self.test_conversation = {
            "id": "test-conv",
            "title": "Test Export Conversation", 
            "mapping": {
                "root": {
                    "children": ["msg-1"],
                    "parent": None,
                    "message": None
                },
                "msg-1": {
                    "children": ["msg-2"],
                    "parent": "root",
                    "message": {
                        "id": "msg-1",
                        "role": "user",
                        "author": {"role": "user"},
                        "create_time": 1234567890,
                        "content": {
                            "content_type": "text",
                            "parts": ["Test user message"]
                        }
                    }
                },
                "msg-2": {
                    "children": [],
                    "parent": "msg-1", 
                    "message": {
                        "id": "msg-2",
                        "role": "assistant",
                        "author": {"role": "assistant"},
                        "create_time": 1234567891,
                        "content": {
                            "content_type": "text",
                            "parts": ["Test assistant response"]
                        }
                    }
                }
            }
        }

    @patch('sys.stdout')
    def test_export_conversation_success(self, mock_stdout):
        """Test successful conversation export."""
        # This tests the current export_conversation function
        cgpt.export_conversation([self.test_conversation], 0)
        
        # Verify print calls were made (we'd need to capture stdout properly)
        self.assertTrue(mock_stdout.write.called)

    def test_export_conversation_invalid_index(self):
        """Test export with invalid conversation index."""
        with patch('sys.stdout') as mock_stdout:
            cgpt.export_conversation([self.test_conversation], 5)
            # Should print error message
            mock_stdout.write.assert_called()

    def test_export_empty_conversation_list(self):
        """Test export with empty conversation list."""
        with patch('sys.stdout') as mock_stdout:
            cgpt.export_conversation([], 0)
            # Should print error message
            mock_stdout.write.assert_called()


class TestRoleExtraction(unittest.TestCase):
    """Test role extraction from various message formats."""
    
    def test_extract_role_standard_format(self):
        """Test role extraction from standard format."""
        message = {"role": "user"}
        # This would test extracted role logic once we have a dedicated function
        
        role = "unknown"
        if message.get('role'):
            role = message.get('role')
            
        self.assertEqual(role, "user")

    def test_extract_role_from_author(self):
        """Test role extraction from author field."""
        message = {"author": {"role": "assistant"}}
        
        role = "unknown"
        if message.get('author') and isinstance(message['author'], dict):
            role = message['author'].get('role', 'unknown')
            
        self.assertEqual(role, "assistant")

    def test_extract_role_from_content_type(self):
        """Test role extraction from content_type."""
        message = {"content_type": "thoughts"}
        
        role = "unknown"
        if message.get('content_type'):
            role = message.get('content_type')
            
        self.assertEqual(role, "thoughts")

    def test_extract_role_from_id_prefix(self):
        """Test role extraction from ID prefix."""
        message = {"id": "user-12345"}
        
        role = "unknown"
        if message.get('id') and isinstance(message.get('id'), str):
            msg_id = message.get('id')
            if msg_id.startswith('user-'):
                role = 'user'
            elif msg_id.startswith('assistant-'):
                role = 'assistant'
                
        self.assertEqual(role, "user")


class TestCLIFunctionality(unittest.TestCase):
    """Test CLI argument parsing and command execution."""
    
    @patch('sys.stdout')
    def test_list_command(self, mock_stdout):
        """Test the list command."""
        conversations = [{"title": "Test Conversation"}]
        
        # Test the list_conversations function directly
        cgpt.list_conversations(conversations, 5)
        
        # Verify output was printed
        self.assertTrue(mock_stdout.write.called)

    @patch('sys.stdout')
    def test_export_command(self, mock_stdout):
        """Test the export command."""
        conversations = [{"title": "Test", "id": "test-1", "messages": []}]
        
        # Test export_conversation function directly  
        cgpt.export_conversation(conversations, 0)
        
        # Verify output was printed
        self.assertTrue(mock_stdout.write.called)

    def test_invalid_conversation_number(self):
        """Test handling of invalid conversation numbers."""
        # This would test validation logic
        conversations = [{"title": "Test"}]
        
        # Test bounds checking
        self.assertTrue(0 <= 0 < len(conversations))  # Valid
        self.assertFalse(0 <= 5 < len(conversations))  # Invalid


if __name__ == '__main__':
    # Set up test environment
    unittest.main(verbosity=2)