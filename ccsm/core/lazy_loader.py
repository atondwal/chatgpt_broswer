#!/usr/bin/env python3
"""Lazy loading implementation for conversation data."""

import json
import weakref
from pathlib import Path
from typing import List, Dict, Optional, Iterator, Any, Callable
from dataclasses import dataclass, field
from threading import Lock

from ccsm.core.models import Conversation, Message
from ccsm.core.logging_config import get_logger
from ccsm.core.type_definitions import ConversationDict, Timestamp

logger = get_logger(__name__)


@dataclass
class ConversationMetadata:
    """Lightweight metadata for a conversation without full content."""
    id: str
    title: str
    file_path: Optional[str] = None
    create_time: Optional[Timestamp] = None
    update_time: Optional[Timestamp] = None
    message_count: int = 0
    file_size: Optional[int] = None
    last_accessed: Optional[Timestamp] = None
    
    def to_conversation_stub(self) -> Conversation:
        """Create a conversation stub with empty messages."""
        return Conversation(
            id=self.id,
            title=self.title,
            messages=[],  # Empty - will be loaded on demand
            create_time=self.create_time,
            update_time=self.update_time
        )


class ConversationCache:
    """LRU cache for loaded conversations with memory management."""
    
    def __init__(self, max_size: int = 50, max_memory_mb: int = 100):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: Dict[str, Conversation] = {}
        self.access_order: List[str] = []
        self.memory_usage = 0
        self.lock = Lock()
        self.logger = get_logger(__name__)
    
    def get(self, conv_id: str) -> Optional[Conversation]:
        """Get conversation from cache, updating access order."""
        with self.lock:
            if conv_id in self.cache:
                # Move to end (most recently used)
                self.access_order.remove(conv_id)
                self.access_order.append(conv_id)
                return self.cache[conv_id]
            return None
    
    def put(self, conversation: Conversation) -> None:
        """Add conversation to cache, evicting if necessary."""
        with self.lock:
            conv_id = conversation.id
            
            # Calculate memory usage
            conv_size = self._estimate_conversation_size(conversation)
            
            # Remove existing entry if present
            if conv_id in self.cache:
                self.access_order.remove(conv_id)
                old_size = self._estimate_conversation_size(self.cache[conv_id])
                self.memory_usage -= old_size
            
            # Evict if necessary
            while (len(self.cache) >= self.max_size or 
                   self.memory_usage + conv_size > self.max_memory_bytes):
                if not self.access_order:
                    break
                self._evict_oldest()
            
            # Add new conversation
            self.cache[conv_id] = conversation
            self.access_order.append(conv_id)
            self.memory_usage += conv_size
            
            self.logger.debug(f"Cached conversation {conv_id}, memory usage: {self.memory_usage / 1024 / 1024:.1f}MB")
    
    def remove(self, conv_id: str) -> None:
        """Remove conversation from cache."""
        with self.lock:
            if conv_id in self.cache:
                self.access_order.remove(conv_id)
                conv_size = self._estimate_conversation_size(self.cache[conv_id])
                del self.cache[conv_id]
                self.memory_usage -= conv_size
    
    def clear(self) -> None:
        """Clear all cached conversations."""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
            self.memory_usage = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'memory_usage_mb': self.memory_usage / 1024 / 1024,
                'max_memory_mb': self.max_memory_bytes / 1024 / 1024,
                'hit_rate': getattr(self, '_hit_count', 0) / max(getattr(self, '_total_requests', 1), 1)
            }
    
    def _evict_oldest(self) -> None:
        """Evict the oldest conversation from cache."""
        if self.access_order:
            oldest_id = self.access_order.pop(0)
            if oldest_id in self.cache:
                conv_size = self._estimate_conversation_size(self.cache[oldest_id])
                del self.cache[oldest_id]
                self.memory_usage -= conv_size
                self.logger.debug(f"Evicted conversation {oldest_id}")
    
    def _estimate_conversation_size(self, conversation: Conversation) -> int:
        """Estimate memory usage of a conversation in bytes."""
        # Rough estimation based on string content
        size = len(conversation.title) * 2  # Unicode overhead
        size += len(conversation.id) * 2
        
        for message in conversation.messages:
            size += len(message.content) * 2
            size += len(message.id) * 2
            size += 100  # Overhead for Message object
        
        size += 200  # Overhead for Conversation object
        return size


class LazyConversationLoader:
    """Lazy loader for conversations with metadata-first approach."""
    
    def __init__(self, cache_size: int = 50, cache_memory_mb: int = 100):
        self.cache = ConversationCache(cache_size, cache_memory_mb)
        self.metadata_cache: Dict[str, ConversationMetadata] = {}
        self.loaders: Dict[str, Callable[[str], Optional[Conversation]]] = {}
        self.logger = get_logger(__name__)
    
    def register_loader(self, format_name: str, loader_func: Callable[[str], Optional[Conversation]]) -> None:
        """Register a loader function for a specific format."""
        self.loaders[format_name] = loader_func
        self.logger.debug(f"Registered loader for format: {format_name}")
    
    def scan_conversations(self, file_path: str, format: str = "auto") -> List[ConversationMetadata]:
        """Scan and extract metadata without loading full conversations."""
        self.logger.info(f"Scanning conversations from {file_path}")
        
        path = Path(file_path)
        metadata_list = []
        
        if path.is_dir():
            # Directory scanning (Claude projects)
            metadata_list = self._scan_directory(path)
        elif path.is_file():
            # Single file scanning (ChatGPT exports)
            metadata_list = self._scan_file(path, format)
        
        # Cache metadata
        for metadata in metadata_list:
            self.metadata_cache[metadata.id] = metadata
        
        self.logger.info(f"Scanned {len(metadata_list)} conversations")
        return metadata_list
    
    def load_conversation(self, conv_id: str) -> Optional[Conversation]:
        """Load a specific conversation by ID, using cache if available."""
        # Check cache first
        cached = self.cache.get(conv_id)
        if cached:
            return cached
        
        # Get metadata
        metadata = self.metadata_cache.get(conv_id)
        if not metadata:
            self.logger.warning(f"No metadata found for conversation {conv_id}")
            return None
        
        # Load from file
        conversation = self._load_from_metadata(metadata)
        if conversation:
            self.cache.put(conversation)
        
        return conversation
    
    def get_conversation_metadata(self, conv_id: str) -> Optional[ConversationMetadata]:
        """Get metadata for a conversation without loading full content."""
        return self.metadata_cache.get(conv_id)
    
    def get_all_metadata(self) -> List[ConversationMetadata]:
        """Get metadata for all scanned conversations."""
        return list(self.metadata_cache.values())
    
    def preload_conversations(self, conv_ids: List[str], max_concurrent: int = 5) -> None:
        """Preload specific conversations in the background."""
        import concurrent.futures
        
        def load_single(conv_id: str) -> None:
            try:
                self.load_conversation(conv_id)
            except Exception as e:
                self.logger.error(f"Error preloading conversation {conv_id}: {e}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = [executor.submit(load_single, conv_id) for conv_id in conv_ids[:10]]  # Limit to 10
            concurrent.futures.wait(futures, timeout=30.0)
        
        self.logger.info(f"Preloaded conversations for {len(conv_ids)} IDs")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get loader and cache statistics."""
        stats = self.cache.get_stats()
        stats.update({
            'metadata_count': len(self.metadata_cache),
            'registered_loaders': list(self.loaders.keys())
        })
        return stats
    
    def _scan_directory(self, path: Path) -> List[ConversationMetadata]:
        """Scan a directory for conversation files."""
        metadata_list = []
        
        for jsonl_file in path.glob("*.jsonl"):
            try:
                metadata = self._extract_file_metadata(jsonl_file, "claude")
                if metadata:
                    metadata_list.append(metadata)
            except Exception as e:
                self.logger.error(f"Error scanning {jsonl_file}: {e}")
        
        return metadata_list
    
    def _scan_file(self, path: Path, format: str) -> List[ConversationMetadata]:
        """Scan a single file for conversations."""
        try:
            if format == "auto":
                format = "claude" if path.suffix == ".jsonl" else "chatgpt"
            
            if format == "chatgpt":
                return self._scan_chatgpt_file(path)
            elif format == "claude":
                metadata = self._extract_file_metadata(path, format)
                return [metadata] if metadata else []
        except Exception as e:
            self.logger.error(f"Error scanning file {path}: {e}")
        
        return []
    
    def _scan_chatgpt_file(self, path: Path) -> List[ConversationMetadata]:
        """Scan ChatGPT export file for conversation metadata."""
        metadata_list = []
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for conv_data in data:
                    if isinstance(conv_data, dict) and 'id' in conv_data:
                        metadata = ConversationMetadata(
                            id=conv_data['id'],
                            title=conv_data.get('title', 'Untitled'),
                            file_path=str(path),
                            create_time=conv_data.get('create_time'),
                            update_time=conv_data.get('update_time'),
                            message_count=len(conv_data.get('messages', []))
                        )
                        metadata_list.append(metadata)
        
        except Exception as e:
            self.logger.error(f"Error scanning ChatGPT file {path}: {e}")
        
        return metadata_list
    
    def _extract_file_metadata(self, path: Path, format: str) -> Optional[ConversationMetadata]:
        """Extract metadata from a conversation file without loading full content."""
        try:
            stat = path.stat()
            
            # For Claude files, use filename as ID
            conv_id = path.stem
            title = "Loading..."  # Will be updated when loaded
            message_count = 0
            first_timestamp = None
            last_timestamp = None
            
            # Quick scan for basic info
            if format == "claude":
                with open(path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f):
                        if line_num > 10:  # Only scan first few lines for metadata
                            break
                        
                        if line.strip():
                            try:
                                data = json.loads(line)
                                if 'timestamp' in data:
                                    from ccsm.core.claude_loader import parse_timestamp
                                    ts = parse_timestamp(data['timestamp'])
                                    if ts:
                                        if first_timestamp is None:
                                            first_timestamp = ts
                                        last_timestamp = ts
                                message_count += 1
                            except json.JSONDecodeError:
                                continue
            
            return ConversationMetadata(
                id=conv_id,
                title=title,
                file_path=str(path),
                create_time=first_timestamp,
                update_time=last_timestamp or stat.st_mtime,
                message_count=message_count,
                file_size=stat.st_size
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting metadata from {path}: {e}")
            return None
    
    def _load_from_metadata(self, metadata: ConversationMetadata) -> Optional[Conversation]:
        """Load full conversation from metadata."""
        if not metadata.file_path:
            return None
        
        # Determine format from file path
        path = Path(metadata.file_path)
        if path.suffix == ".jsonl":
            format_name = "claude"
        else:
            format_name = "chatgpt"
        
        # Use registered loader
        loader = self.loaders.get(format_name)
        if not loader:
            self.logger.error(f"No loader registered for format: {format_name}")
            return None
        
        # Load conversation
        conversation = loader(metadata.file_path)
        if conversation and conversation.id != metadata.id:
            # Update conversation ID to match metadata
            conversation.id = metadata.id
        
        return conversation