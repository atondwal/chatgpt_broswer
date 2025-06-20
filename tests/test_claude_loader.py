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
        claude_msg = {
            "role": "user", 
            "content": "Hello Claude!"
        }
        
        msg = parse_claude_message(claude_msg, "msg1")
        assert msg.id == "msg1"
        assert msg.role.value == "user"
        assert msg.content == "Hello Claude!"
    
    def test_parse_claude_message_assistant(self):
        """Test parsing assistant message."""
        claude_msg = {
            "role": "assistant",
            "content": "Hello! How can I help you?"
        }
        
        msg = parse_claude_message(claude_msg, "msg2")
        assert msg.id == "msg2"
        assert msg.role.value == "assistant"
        assert msg.content == "Hello! How can I help you?"
    
    def test_parse_claude_message_with_text_content(self):
        """Test parsing message with text field."""
        claude_msg = {
            "role": "user",
            "content": {
                "text": "What is Python?"
            }
        }
        
        msg = parse_claude_message(claude_msg, "msg3")
        assert msg.content == "What is Python?"
    
    def test_parse_claude_message_empty_content(self):
        """Test parsing message with no content."""
        claude_msg = {
            "role": "user"
        }
        
        msg = parse_claude_message(claude_msg, "msg4")
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
        claude_data = {
            "id": "claude_conv_1",
            "name": "Python Discussion",
            "created_at": "2024-01-01T10:00:00Z",
            "messages": [
                {
                    "role": "user",
                    "content": "What is Python?"
                },
                {
                    "role": "assistant", 
                    "content": "Python is a programming language."
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(json.dumps(claude_data) + '\n')
            test_file = f.name
        
        try:
            conversations = load_claude_conversations(test_file)
            assert len(conversations) == 1
            
            conv = conversations[0]
            assert conv.id == "claude_conv_1"
            assert conv.title == "Python Discussion"
            assert len(conv.messages) == 2
            assert conv.messages[0].content == "What is Python?"
            assert conv.messages[1].content == "Python is a programming language."
        finally:
            Path(test_file).unlink(missing_ok=True)
    
    def test_load_claude_conversations_multiple(self):
        """Test loading multiple Claude conversations."""
        conv1 = {
            "id": "conv1",
            "name": "First Chat",
            "created_at": "2024-01-01T10:00:00Z",
            "messages": [{"role": "user", "content": "Hello"}]
        }
        
        conv2 = {
            "id": "conv2", 
            "name": "Second Chat",
            "created_at": "2024-01-02T10:00:00Z",
            "messages": [{"role": "user", "content": "Hi again"}]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(json.dumps(conv1) + '\n')
            f.write(json.dumps(conv2) + '\n')
            test_file = f.name
        
        try:
            conversations = load_claude_conversations(test_file)
            assert len(conversations) == 2
            assert conversations[0].title == "First Chat"
            assert conversations[1].title == "Second Chat"
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
        incomplete_conv = {
            "id": "incomplete",
            # Missing name and created_at
            "messages": []
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(json.dumps(incomplete_conv) + '\n')
            test_file = f.name
        
        try:
            conversations = load_claude_conversations(test_file)
            if conversations:
                conv = conversations[0]
                assert conv.id == "incomplete"
                # Should handle missing fields gracefully
                assert conv.title is not None  # Should have some default
        finally:
            Path(test_file).unlink(missing_ok=True)
    
    def test_created_at_parsing(self):
        """Test parsing different created_at formats."""
        claude_data = {
            "id": "time_conv",
            "name": "Time Test",
            "created_at": "2024-01-15T14:30:00Z",
            "messages": []
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(json.dumps(claude_data) + '\n')
            test_file = f.name
        
        try:
            conversations = load_claude_conversations(test_file)
            if conversations:
                conv = conversations[0]
                assert conv.create_time is not None
                assert isinstance(conv.create_time, (int, float))
        finally:
            Path(test_file).unlink(missing_ok=True)