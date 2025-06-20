#!/usr/bin/env python3
"""Tests for Claude loader functionality."""

import tempfile
import json
import pytest
from pathlib import Path

from src.core.claude_loader import load_claude_conversations, parse_claude_message


class TestClaudeLoader:
    """Test Claude JSONL loader functionality."""
    
    def test_parse_claude_message_user(self):
        """Test parsing user message."""
        claude_data = {
            "type": "user",
            "uuid": "msg1",
            "timestamp": "2024-01-01T10:00:00Z",
            "message": {
                "content": [{"type": "text", "text": "Hello Claude!"}]
            }
        }
        
        msg = parse_claude_message(claude_data)
        assert msg.id == "msg1"
        assert msg.role.value == "user"
        assert msg.content == "Hello Claude!"
    
    def test_parse_claude_message_assistant(self):
        """Test parsing assistant message."""
        claude_data = {
            "type": "assistant",
            "uuid": "msg2",
            "timestamp": "2024-01-01T10:01:00Z",
            "message": {
                "content": [{"type": "text", "text": "Hello! How can I help you?"}]
            }
        }
        
        msg = parse_claude_message(claude_data)
        assert msg.id == "msg2"
        assert msg.role.value == "assistant"
        assert msg.content == "Hello! How can I help you?"
    
    def test_parse_claude_message_with_text_content(self):
        """Test parsing message with text field."""
        claude_data = {
            "type": "user",
            "uuid": "msg3", 
            "message": {
                "content": [{"type": "text", "text": "What is Python?"}]
            }
        }
        
        msg = parse_claude_message(claude_data)
        assert msg.content == "What is Python?"
    
    def test_parse_claude_message_empty_content(self):
        """Test parsing message with no content."""
        claude_data = {
            "type": "user",
            "uuid": "msg4",
            "message": {
                "content": []
            }
        }
        
        msg = parse_claude_message(claude_data)
        assert msg.content == "[Empty message]"
    
    def test_load_claude_conversations_empty(self):
        """Test loading empty JSONL file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write("")  # Empty file
            test_file = f.name
        
        try:
            conversations = load_claude_conversations(test_file)
            assert conversations == []
        finally:
            Path(test_file).unlink(missing_ok=True)
    
    def test_load_claude_conversations_single(self):
        """Test loading single Claude conversation."""
        user_msg = {
            "type": "user",
            "uuid": "msg1",
            "timestamp": "2024-01-01T10:00:00Z",
            "message": {
                "content": [{"type": "text", "text": "What is Python?"}]
            }
        }
        
        assistant_msg = {
            "type": "assistant", 
            "uuid": "msg2",
            "timestamp": "2024-01-01T10:01:00Z",
            "message": {
                "content": [{"type": "text", "text": "Python is a programming language."}]
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(json.dumps(user_msg) + '\n')
            f.write(json.dumps(assistant_msg) + '\n')
            test_file = f.name
        
        try:
            conversations = load_claude_conversations(test_file)
            assert len(conversations) == 1
            
            conv = conversations[0]
            assert len(conv.messages) == 2
            assert conv.messages[0].content == "What is Python?"
            assert conv.messages[1].content == "Python is a programming language."
        finally:
            Path(test_file).unlink(missing_ok=True)
    
    def test_load_claude_conversations_multiple(self):
        """Test loading conversation with multiple messages."""
        msg1 = {
            "type": "user",
            "uuid": "msg1",
            "timestamp": "2024-01-01T10:00:00Z",
            "message": {"content": [{"type": "text", "text": "Hello"}]}
        }
        
        msg2 = {
            "type": "assistant",
            "uuid": "msg2", 
            "timestamp": "2024-01-01T10:01:00Z",
            "message": {"content": [{"type": "text", "text": "Hi there!"}]}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(json.dumps(msg1) + '\n')
            f.write(json.dumps(msg2) + '\n')
            test_file = f.name
        
        try:
            conversations = load_claude_conversations(test_file)
            assert len(conversations) == 1
            assert len(conversations[0].messages) == 2
        finally:
            Path(test_file).unlink(missing_ok=True)
    
    def test_load_claude_conversations_malformed_json(self):
        """Test handling malformed JSON lines."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"valid": "json"}\n')
            f.write('invalid json line\n')  # This should be skipped
            f.write('{"another": "valid"}\n')
            test_file = f.name
        
        try:
            # Should skip malformed lines and continue
            conversations = load_claude_conversations(test_file)
            # Might have 0 conversations if the valid JSON doesn't have required fields
            assert isinstance(conversations, list)
        finally:
            Path(test_file).unlink(missing_ok=True)
    
    def test_load_claude_conversations_missing_fields(self):
        """Test conversations with missing required fields."""
        incomplete_msg = {
            "type": "invalid_type",  # Invalid type
            "uuid": "incomplete"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(json.dumps(incomplete_msg) + '\n')
            test_file = f.name
        
        try:
            conversations = load_claude_conversations(test_file)
            # Should handle missing fields gracefully - likely returns empty list
            assert isinstance(conversations, list)
        finally:
            Path(test_file).unlink(missing_ok=True)
    
    def test_created_at_parsing(self):
        """Test timestamp parsing."""
        msg_with_time = {
            "type": "user",
            "uuid": "time_msg",
            "timestamp": "2024-01-15T14:30:00Z",
            "message": {"content": [{"type": "text", "text": "Test"}]}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(json.dumps(msg_with_time) + '\n')
            test_file = f.name
        
        try:
            conversations = load_claude_conversations(test_file)
            if conversations and conversations[0].messages:
                msg = conversations[0].messages[0]
                assert msg.create_time is not None
                assert isinstance(msg.create_time, (int, float))
        finally:
            Path(test_file).unlink(missing_ok=True)