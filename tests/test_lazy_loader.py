#!/usr/bin/env python3
"""Tests for lazy loading functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from chatgpt_browser.core.lazy_loader import (
    ConversationMetadata, 
    ConversationCache, 
    LazyConversationLoader
)
from chatgpt_browser.core.models import Conversation, Message, MessageRole


class TestConversationMetadata:
    """Test ConversationMetadata functionality."""
    
    def test_metadata_creation(self):
        """Test creating conversation metadata."""
        metadata = ConversationMetadata(
            id="test_id",
            title="Test Conversation",
            file_path="/test/path.jsonl",
            message_count=5,
            file_size=1024
        )
        
        assert metadata.id == "test_id"
        assert metadata.title == "Test Conversation"
        assert metadata.file_path == "/test/path.jsonl"
        assert metadata.message_count == 5
        assert metadata.file_size == 1024
    
    def test_to_conversation_stub(self):
        """Test creating conversation stub from metadata."""
        metadata = ConversationMetadata(
            id="test_id",
            title="Test Conversation",
            create_time=1234567890,
            update_time=1234567891
        )
        
        stub = metadata.to_conversation_stub()
        
        assert isinstance(stub, Conversation)
        assert stub.id == "test_id"
        assert stub.title == "Test Conversation"
        assert stub.messages == []
        assert stub.create_time == 1234567890
        assert stub.update_time == 1234567891


class TestConversationCache:
    """Test ConversationCache functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = ConversationCache(max_size=3, max_memory_mb=1)  # Small limits for testing
        self.test_conversation = Conversation(
            id="test_id",
            title="Test Conversation",
            messages=[
                Message(id="msg1", role=MessageRole.USER, content="Hello"),
                Message(id="msg2", role=MessageRole.ASSISTANT, content="Hi there!")
            ]
        )
    
    def test_cache_creation(self):
        """Test cache creation with limits."""
        assert self.cache.max_size == 3
        assert self.cache.max_memory_bytes == 1024 * 1024
        assert len(self.cache.cache) == 0
        assert len(self.cache.access_order) == 0
        assert self.cache.memory_usage == 0
    
    def test_put_and_get(self):
        """Test putting and getting conversations from cache."""
        # Put conversation
        self.cache.put(self.test_conversation)
        
        # Verify it's cached
        assert len(self.cache.cache) == 1
        assert "test_id" in self.cache.cache
        assert "test_id" in self.cache.access_order
        assert self.cache.memory_usage > 0
        
        # Get conversation
        retrieved = self.cache.get("test_id")
        assert retrieved is not None
        assert retrieved.id == "test_id"
        assert retrieved.title == "Test Conversation"
        
        # Verify access order updated (moved to end)
        assert self.cache.access_order[-1] == "test_id"
    
    def test_get_nonexistent(self):
        """Test getting non-existent conversation."""
        result = self.cache.get("nonexistent")
        assert result is None
    
    def test_lru_eviction_by_size(self):
        """Test LRU eviction when size limit exceeded."""
        # Add conversations up to limit
        for i in range(4):  # Exceeds max_size of 3
            conv = Conversation(
                id=f"conv_{i}",
                title=f"Conversation {i}",
                messages=[Message(id=f"msg_{i}", role=MessageRole.USER, content=f"Message {i}")]
            )
            self.cache.put(conv)
        
        # Should have only 3 conversations (oldest evicted)
        assert len(self.cache.cache) == 3
        assert "conv_0" not in self.cache.cache  # First one should be evicted
        assert "conv_1" in self.cache.cache
        assert "conv_2" in self.cache.cache
        assert "conv_3" in self.cache.cache
    
    def test_update_existing_entry(self):
        """Test updating existing cache entry."""
        # Put initial conversation
        self.cache.put(self.test_conversation)
        initial_memory = self.cache.memory_usage
        
        # Update with modified conversation
        updated_conv = Conversation(
            id="test_id",
            title="Updated Conversation",
            messages=[Message(id="msg1", role=MessageRole.USER, content="Updated message")]
        )
        self.cache.put(updated_conv)
        
        # Should still have one entry
        assert len(self.cache.cache) == 1
        
        # Should have updated content
        retrieved = self.cache.get("test_id")
        assert retrieved.title == "Updated Conversation"
    
    def test_remove(self):
        """Test removing conversation from cache."""
        self.cache.put(self.test_conversation)
        assert len(self.cache.cache) == 1
        
        self.cache.remove("test_id")
        assert len(self.cache.cache) == 0
        assert "test_id" not in self.cache.access_order
        assert self.cache.memory_usage == 0
    
    def test_clear(self):
        """Test clearing entire cache."""
        # Add multiple conversations
        for i in range(2):
            conv = Conversation(
                id=f"conv_{i}",
                title=f"Conversation {i}",
                messages=[]
            )
            self.cache.put(conv)
        
        assert len(self.cache.cache) == 2
        
        self.cache.clear()
        assert len(self.cache.cache) == 0
        assert len(self.cache.access_order) == 0
        assert self.cache.memory_usage == 0
    
    def test_get_stats(self):
        """Test getting cache statistics."""
        self.cache.put(self.test_conversation)
        stats = self.cache.get_stats()
        
        assert stats['size'] == 1
        assert stats['max_size'] == 3
        assert stats['memory_usage_mb'] > 0
        assert stats['max_memory_mb'] == 1.0
        assert 'hit_rate' in stats


class TestLazyConversationLoader:
    """Test LazyConversationLoader functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.loader = LazyConversationLoader(cache_size=10, cache_memory_mb=10)
    
    def test_loader_creation(self):
        """Test loader creation."""
        assert isinstance(self.loader.cache, ConversationCache)
        assert len(self.loader.metadata_cache) == 0
        assert len(self.loader.loaders) == 0
    
    def test_register_loader(self):
        """Test registering a loader function."""
        def mock_loader(file_path: str):
            return Conversation(id="test", title="Test", messages=[])
        
        self.loader.register_loader("test_format", mock_loader)
        
        assert "test_format" in self.loader.loaders
        assert self.loader.loaders["test_format"] == mock_loader
    
    def test_scan_chatgpt_file(self):
        """Test scanning ChatGPT export file."""
        # Create test data
        test_data = [
            {
                "id": "conv1",
                "title": "First Conversation",
                "create_time": 1234567890,
                "update_time": 1234567891,
                "messages": [{"id": "msg1", "content": "Hello"}]
            },
            {
                "id": "conv2", 
                "title": "Second Conversation",
                "create_time": 1234567892,
                "update_time": 1234567893,
                "messages": [{"id": "msg2", "content": "Hi"}]
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_file = f.name
        
        try:
            # Scan the file
            metadata_list = self.loader.scan_conversations(temp_file, format="chatgpt")
            
            assert len(metadata_list) == 2
            
            # Check first conversation metadata
            meta1 = next(m for m in metadata_list if m.id == "conv1")
            assert meta1.title == "First Conversation"
            assert meta1.create_time == 1234567890
            assert meta1.update_time == 1234567891
            assert meta1.message_count == 1
            assert meta1.file_path == temp_file
            
            # Check second conversation metadata
            meta2 = next(m for m in metadata_list if m.id == "conv2")
            assert meta2.title == "Second Conversation"
            assert meta2.create_time == 1234567892
            assert meta2.update_time == 1234567893
            assert meta2.message_count == 1
            
            # Verify metadata is cached
            assert len(self.loader.metadata_cache) == 2
            assert "conv1" in self.loader.metadata_cache
            assert "conv2" in self.loader.metadata_cache
            
        finally:
            Path(temp_file).unlink()
    
    def test_scan_claude_directory(self):
        """Test scanning Claude project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test JSONL files
            for i in range(2):
                jsonl_file = temp_path / f"conversation_{i}.jsonl"
                with open(jsonl_file, 'w') as f:
                    f.write(f'{{"type": "user", "timestamp": "2024-01-0{i+1}T10:00:00Z", "message": {{"content": [{{"type": "text", "text": "Hello {i}"}}]}}}}\n')
                    f.write(f'{{"type": "assistant", "timestamp": "2024-01-0{i+1}T10:01:00Z", "message": {{"content": [{{"type": "text", "text": "Hi {i}"}}]}}}}\n')
            
            # Scan directory
            metadata_list = self.loader.scan_conversations(str(temp_path), format="claude")
            
            assert len(metadata_list) == 2
            
            # Check metadata
            for metadata in metadata_list:
                assert metadata.id in ["conversation_0", "conversation_1"]
                assert metadata.title == "Loading..."  # Default title before loading
                assert metadata.message_count == 2  # 2 messages per file
                assert metadata.file_size > 0
    
    def test_load_conversation_with_cache(self):
        """Test loading conversation with caching."""
        # Create mock loader
        mock_conversation = Conversation(
            id="test_id",
            title="Test Conversation", 
            messages=[Message(id="msg1", role=MessageRole.USER, content="Hello")]
        )
        
        def mock_loader(file_path: str):
            return mock_conversation
        
        # Register loader for json format (since file path ends with .json)
        self.loader.register_loader("chatgpt", mock_loader)
        
        # Add metadata
        metadata = ConversationMetadata(
            id="test_id",
            title="Test Conversation",
            file_path="/fake/path.json"
        )
        self.loader.metadata_cache["test_id"] = metadata
        
        # Load conversation (should call loader and cache result)
        result = self.loader.load_conversation("test_id")
        
        assert result is not None
        assert result.id == "test_id"
        assert result.title == "Test Conversation"
        
        # Verify it's cached
        cached_result = self.loader.cache.get("test_id")
        assert cached_result is not None
        assert cached_result.id == "test_id"
        
        # Load again (should come from cache)
        result2 = self.loader.load_conversation("test_id")
        assert result2 is result  # Same object from cache
    
    def test_load_conversation_no_metadata(self):
        """Test loading conversation with no metadata."""
        result = self.loader.load_conversation("nonexistent")
        assert result is None
    
    def test_load_conversation_no_loader(self):
        """Test loading conversation with no registered loader."""
        # Add metadata but no loader
        metadata = ConversationMetadata(
            id="test_id",
            title="Test Conversation",
            file_path="/fake/path.unknown"
        )
        self.loader.metadata_cache["test_id"] = metadata
        
        result = self.loader.load_conversation("test_id")
        assert result is None
    
    def test_get_conversation_metadata(self):
        """Test getting conversation metadata."""
        metadata = ConversationMetadata(
            id="test_id",
            title="Test Conversation"
        )
        self.loader.metadata_cache["test_id"] = metadata
        
        result = self.loader.get_conversation_metadata("test_id")
        assert result is metadata
        
        result2 = self.loader.get_conversation_metadata("nonexistent")
        assert result2 is None
    
    def test_get_all_metadata(self):
        """Test getting all metadata."""
        # Add multiple metadata entries
        for i in range(3):
            metadata = ConversationMetadata(
                id=f"conv_{i}",
                title=f"Conversation {i}"
            )
            self.loader.metadata_cache[f"conv_{i}"] = metadata
        
        all_metadata = self.loader.get_all_metadata()
        assert len(all_metadata) == 3
        assert all(isinstance(m, ConversationMetadata) for m in all_metadata)
    
    def test_preload_conversations(self):
        """Test preloading conversations in background."""
        # Add test metadata
        for i in range(3):
            metadata = ConversationMetadata(
                id=f"conv_{i}",
                title=f"Conversation {i}",
                file_path=f"/fake/path_{i}.json"
            )
            self.loader.metadata_cache[f"conv_{i}"] = metadata
        
        # Register mock loader
        def mock_loader(file_path: str):
            conv_id = Path(file_path).stem.split('_')[-1]
            return Conversation(id=f"conv_{conv_id}", title=f"Conversation {conv_id}", messages=[])
        
        self.loader.register_loader("chatgpt", mock_loader)
        
        # Mock the ThreadPoolExecutor to avoid actual threading
        with patch('concurrent.futures.ThreadPoolExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor_class.return_value.__enter__.return_value = mock_executor
            
            # Mock futures.wait to return immediately
            with patch('concurrent.futures.wait') as mock_wait:
                conv_ids = ["conv_0", "conv_1", "conv_2"]
                self.loader.preload_conversations(conv_ids)
                
                # Verify executor was called
                mock_executor_class.assert_called_once_with(max_workers=5)
                assert mock_executor.submit.call_count == 3
                mock_wait.assert_called_once()
    
    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        # Add some metadata
        metadata = ConversationMetadata(id="test", title="Test")
        self.loader.metadata_cache["test"] = metadata
        
        # Register a loader
        self.loader.register_loader("test_format", lambda x: None)
        
        stats = self.loader.get_cache_stats()
        
        assert 'size' in stats
        assert 'metadata_count' in stats
        assert 'registered_loaders' in stats
        assert stats['metadata_count'] == 1
        assert "test_format" in stats['registered_loaders']


class TestLazyLoaderIntegration:
    """Integration tests for lazy loader with real file operations."""
    
    def test_scan_and_load_integration(self):
        """Test complete scan and load workflow."""
        # Create test ChatGPT export
        test_data = [
            {
                "id": "integration_test",
                "title": "Integration Test Conversation",
                "create_time": 1234567890,
                "update_time": 1234567891,
                "messages": [
                    {"id": "msg1", "role": "user", "content": "Test message"},
                    {"id": "msg2", "role": "assistant", "content": "Test response"}
                ]
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_file = f.name
        
        try:
            loader = LazyConversationLoader()
            
            # Register a simple loader that parses the test data
            def test_loader(file_path: str):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                conv_data = data[0]  # Take first conversation
                return Conversation(
                    id=conv_data['id'],
                    title=conv_data['title'],
                    messages=[
                        Message(
                            id=msg['id'],
                            role=MessageRole.USER if msg['role'] == 'user' else MessageRole.ASSISTANT,
                            content=msg['content']
                        )
                        for msg in conv_data['messages']
                    ],
                    create_time=conv_data['create_time'],
                    update_time=conv_data['update_time']
                )
            
            loader.register_loader("chatgpt", test_loader)
            
            # Scan file
            metadata_list = loader.scan_conversations(temp_file, format="chatgpt")
            assert len(metadata_list) == 1
            
            metadata = metadata_list[0]
            assert metadata.id == "integration_test"
            assert metadata.title == "Integration Test Conversation"
            
            # Load conversation
            conversation = loader.load_conversation("integration_test")
            assert conversation is not None
            assert conversation.id == "integration_test"
            assert conversation.title == "Integration Test Conversation"
            assert len(conversation.messages) == 2
            assert conversation.messages[0].content == "Test message"
            assert conversation.messages[1].content == "Test response"
            
            # Verify caching
            conversation2 = loader.load_conversation("integration_test")
            assert conversation2 is conversation  # Same object from cache
            
        finally:
            Path(temp_file).unlink()