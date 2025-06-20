#!/usr/bin/env python3
"""Tests for core models."""

import pytest
from src.core.models import Conversation, Message, MessageRole


class TestMessageRole:
    """Test MessageRole enum."""
    
    def test_message_role_values(self):
        """Test that MessageRole has expected values."""
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"
    
    def test_message_role_from_string(self):
        """Test creating MessageRole from string."""
        assert MessageRole("user") == MessageRole.USER
        assert MessageRole("assistant") == MessageRole.ASSISTANT
        assert MessageRole("system") == MessageRole.SYSTEM


class TestMessage:
    """Test Message model."""
    
    def test_message_creation(self):
        """Test creating a message."""
        msg = Message("msg1", MessageRole.USER, "Hello world")
        
        assert msg.id == "msg1"
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello world"
    
    def test_message_equality(self):
        """Test message equality comparison."""
        msg1 = Message("msg1", MessageRole.USER, "Hello")
        msg2 = Message("msg1", MessageRole.USER, "Hello")
        msg3 = Message("msg2", MessageRole.USER, "Hello")
        
        assert msg1 == msg2
        assert msg1 != msg3
    
    def test_message_repr(self):
        """Test message string representation."""
        msg = Message("msg1", MessageRole.ASSISTANT, "Test response")
        repr_str = repr(msg)
        
        assert "msg1" in repr_str
        assert "assistant" in repr_str
        assert "Test response" in repr_str


class TestConversation:
    """Test Conversation model."""
    
    def test_conversation_creation_minimal(self):
        """Test creating conversation with minimal data."""
        conv = Conversation("conv1", "Test Chat", [])
        
        assert conv.id == "conv1"
        assert conv.title == "Test Chat"
        assert conv.messages == []
        assert conv.create_time is None
    
    def test_conversation_creation_with_time(self):
        """Test creating conversation with timestamp."""
        conv = Conversation("conv1", "Test Chat", [], create_time=1234567890)
        
        assert conv.create_time == 1234567890
    
    def test_conversation_with_messages(self):
        """Test conversation with messages."""
        messages = [
            Message("msg1", MessageRole.USER, "Hello"),
            Message("msg2", MessageRole.ASSISTANT, "Hi there!")
        ]
        
        conv = Conversation("conv1", "Test Chat", messages)
        
        assert len(conv.messages) == 2
        assert conv.messages[0].content == "Hello"
        assert conv.messages[1].content == "Hi there!"
    
    def test_conversation_equality(self):
        """Test conversation equality comparison."""
        msg1 = Message("msg1", MessageRole.USER, "Hello")
        msg2 = Message("msg1", MessageRole.USER, "Hello")
        
        conv1 = Conversation("conv1", "Title", [msg1])
        conv2 = Conversation("conv1", "Title", [msg2])
        conv3 = Conversation("conv2", "Title", [msg1])
        
        assert conv1 == conv2
        assert conv1 != conv3
    
    def test_conversation_repr(self):
        """Test conversation string representation."""
        conv = Conversation("conv1", "Python Tutorial", [])
        repr_str = repr(conv)
        
        assert "conv1" in repr_str
        assert "Python Tutorial" in repr_str
    
    def test_conversation_message_count(self):
        """Test getting message count."""
        messages = [
            Message("msg1", MessageRole.USER, "Q1"),
            Message("msg2", MessageRole.ASSISTANT, "A1"),
            Message("msg3", MessageRole.USER, "Q2")
        ]
        
        conv = Conversation("conv1", "Multi-turn Chat", messages)
        assert len(conv.messages) == 3


class TestModelEdgeCases:
    """Test edge cases and validation."""
    
    def test_empty_message_content(self):
        """Test message with empty content."""
        msg = Message("msg1", MessageRole.USER, "")
        assert msg.content == ""
    
    def test_none_message_content(self):
        """Test message with None content."""
        msg = Message("msg1", MessageRole.USER, None)
        assert msg.content is None
    
    def test_empty_conversation_title(self):
        """Test conversation with empty title."""
        conv = Conversation("conv1", "", [])
        assert conv.title == ""
    
    def test_none_conversation_title(self):
        """Test conversation with None title."""
        conv = Conversation("conv1", None, [])
        assert conv.title is None
    
    def test_conversation_with_duplicate_message_ids(self):
        """Test conversation with duplicate message IDs."""
        messages = [
            Message("msg1", MessageRole.USER, "First"),
            Message("msg1", MessageRole.ASSISTANT, "Second")  # Same ID
        ]
        
        conv = Conversation("conv1", "Test", messages)
        # Should still work, models don't enforce uniqueness
        assert len(conv.messages) == 2
    
    def test_large_message_content(self):
        """Test message with very large content."""
        large_content = "x" * 10000  # 10k characters
        msg = Message("msg1", MessageRole.USER, large_content)
        
        assert len(msg.content) == 10000
        assert msg.content == large_content
    
    def test_special_characters_in_content(self):
        """Test messages with special characters."""
        special_content = "Hello! 🌟 This has émojis and ñovel characters: \n\t\"quotes\""
        msg = Message("msg1", MessageRole.USER, special_content)
        
        assert msg.content == special_content
    
    def test_conversation_time_edge_cases(self):
        """Test conversation with edge case timestamps."""
        # Zero timestamp
        conv1 = Conversation("conv1", "Test", [], create_time=0)
        assert conv1.create_time == 0
        
        # Negative timestamp (shouldn't happen but should handle)
        conv2 = Conversation("conv2", "Test", [], create_time=-1)
        assert conv2.create_time == -1
        
        # Very large timestamp (year 2038+ problem)
        conv3 = Conversation("conv3", "Test", [], create_time=2147483648)
        assert conv3.create_time == 2147483648