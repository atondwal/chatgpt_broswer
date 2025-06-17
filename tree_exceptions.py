#!/usr/bin/env python3
"""
Custom exception classes for the conversation tree organization system.

Provides specific exception types for better error handling and debugging.
"""

# Standard library imports
import traceback
from typing import Optional, List, Dict, Any

# Third-party imports
# (none currently)

# Local imports
# (none currently)


class TreeError(Exception):
    """Base exception for all tree-related errors with enhanced debugging context."""
    
    def __init__(self, message: str, operation: Optional[str] = None, 
                 node_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.operation = operation
        self.node_id = node_id
        self.message = message
        self.context = context or {}
        self.stack_info = traceback.format_stack()

    def __str__(self) -> str:
        parts = []
        if self.operation:
            parts.append(f"Operation: {self.operation}")
        if self.node_id:
            parts.append(f"Node: {self.node_id}")
        parts.append(f"Error: {self.message}")
        if self.context:
            context_str = ", ".join([f"{k}={v}" for k, v in self.context.items()])
            parts.append(f"Context: {context_str}")
        return " | ".join(parts)
    
    def get_debug_info(self) -> str:
        """Get detailed debugging information including stack trace."""
        info = [str(self)]
        if self.stack_info:
            info.append("Stack trace:")
            info.extend(self.stack_info[-3:])  # Last 3 stack frames
        return "\n".join(info)


class TreeValidationError(TreeError):
    """Raised when tree validation fails."""
    
    def __init__(self, message: str, operation: str, node_id: Optional[str] = None,
                 validation_failures: Optional[List[str]] = None):
        super().__init__(message, operation, node_id)
        self.validation_failures = validation_failures or []


class TreeStructureError(TreeError):
    """Raised when tree structure constraints are violated."""
    pass


class TreeCycleError(TreeStructureError):
    """Raised when an operation would create a cycle in the tree."""
    
    def __init__(self, source_node: str, target_node: str):
        message = f"Moving node '{source_node}' to '{target_node}' would create a cycle"
        super().__init__(message, "move_node", source_node)
        self.source_node = source_node
        self.target_node = target_node


class TreeDepthError(TreeStructureError):
    """Raised when tree depth limit is exceeded."""
    
    def __init__(self, current_depth: int, max_depth: int, node_id: str):
        message = f"Tree depth {current_depth} exceeds maximum {max_depth}"
        super().__init__(message, "create_node", node_id)
        self.current_depth = current_depth
        self.max_depth = max_depth


class TreeCapacityError(TreeStructureError):
    """Raised when folder capacity limits are exceeded."""
    
    def __init__(self, folder_id: str, current_count: int, max_count: int):
        message = f"Folder '{folder_id}' has {current_count} children, exceeds maximum {max_count}"
        super().__init__(message, "add_child", folder_id)
        self.current_count = current_count
        self.max_count = max_count


class NodeNotFoundError(TreeError):
    """Raised when a referenced node doesn't exist."""
    
    def __init__(self, node_id: str, operation: str = "access"):
        message = f"Node '{node_id}' does not exist"
        super().__init__(message, operation, node_id)


class NodeTypeError(TreeError):
    """Raised when a node has an incorrect type for an operation."""
    
    def __init__(self, node_id: str, expected_type: str, actual_type: str, operation: str):
        message = f"Node '{node_id}' is {actual_type}, expected {expected_type}"
        super().__init__(message, operation, node_id)
        self.expected_type = expected_type
        self.actual_type = actual_type


class NodeExistsError(TreeError):
    """Raised when attempting to create a node that already exists."""
    
    def __init__(self, node_id: str, operation: str = "create"):
        message = f"Node '{node_id}' already exists"
        super().__init__(message, operation, node_id)


class MetadataError(TreeError):
    """Raised when metadata operations fail."""
    pass


class StorageError(TreeError):
    """Raised when file storage operations fail."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, 
                 operation: str = "file_operation"):
        super().__init__(message, operation)
        self.file_path = file_path

    def __str__(self) -> str:
        parts = []
        if self.operation:
            parts.append(f"Operation: {self.operation}")
        if self.file_path:
            parts.append(f"File: {self.file_path}")
        parts.append(f"Error: {self.message}")
        return " | ".join(parts)


class FileCorruptionError(StorageError):
    """Raised when organization file is corrupted."""
    
    def __init__(self, file_path: str, details: str):
        message = f"Organization file is corrupted: {details}"
        super().__init__(message, file_path, "load")
        self.details = details


class FilePermissionError(StorageError):
    """Raised when file permission issues occur."""
    
    def __init__(self, file_path: str, operation: str):
        message = f"Permission denied for {operation}"
        super().__init__(message, file_path, operation)


