#!/usr/bin/env python3
"""
Tree operation classes for conversation organization.

Splits the large TreeManager into focused, single-responsibility classes.
"""

# Standard library imports
import logging
import uuid
from typing import Dict, List, Optional, Set, Tuple

# Local imports
from src.tree.tree_constants import (
    ERROR_MESSAGES, MAX_TREE_DEPTH, MAX_CHILDREN_PER_FOLDER
)
from src.tree.tree_types import (
    NodeType, TreeNode, ConversationMetadata, OrganizationData
)


class TreeValidator:
    """Handles validation of tree operations."""
    
    def __init__(self, organization_data: OrganizationData, debug: bool = False):
        self.organization_data = organization_data
        self.debug = debug
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def validate_folder_name(self, name: str) -> None:
        """Validate folder name is not empty."""
        if not name or not name.strip():
            raise ValueError(ERROR_MESSAGES["EMPTY_FOLDER_NAME"])
    
    def validate_parent_exists(self, parent_id: Optional[str]) -> Optional[TreeNode]:
        """Validate parent exists and return it."""
        if parent_id is None:
            return None
        
        if parent_id not in self.organization_data.tree_nodes:
            raise ValueError(ERROR_MESSAGES["PARENT_NOT_FOUND"].format(parent_id=parent_id))
        
        parent = self.organization_data.tree_nodes[parent_id]
        if parent.node_type != NodeType.FOLDER:
            raise ValueError(ERROR_MESSAGES["PARENT_NOT_FOLDER"])
        
        return parent
    
    def validate_node_exists(self, node_id: str) -> TreeNode:
        """Validate node exists and return it."""
        if node_id not in self.organization_data.tree_nodes:
            raise ValueError(ERROR_MESSAGES["NODE_NOT_FOUND"].format(node_id=node_id))
        return self.organization_data.tree_nodes[node_id]
    
    def validate_conversation_not_exists(self, conversation_id: str) -> None:
        """Validate conversation is not already in tree."""
        if conversation_id in self.organization_data.tree_nodes:
            raise ValueError(ERROR_MESSAGES["CONVERSATION_EXISTS"].format(conversation_id=conversation_id))
    
    def validate_tree_depth(self, parent_path: str) -> None:
        """Validate tree depth limit."""
        depth = parent_path.count('/') if parent_path else 0
        if depth >= MAX_TREE_DEPTH:
            raise ValueError(ERROR_MESSAGES["MAX_DEPTH_EXCEEDED"].format(max_depth=MAX_TREE_DEPTH))
    
    def validate_children_limit(self, parent_id: str) -> None:
        """Validate folder children limit."""
        if parent_id in self.organization_data.tree_nodes:
            parent = self.organization_data.tree_nodes[parent_id]
            if len(parent.children) >= MAX_CHILDREN_PER_FOLDER:
                raise ValueError(ERROR_MESSAGES["MAX_CHILDREN_EXCEEDED"].format(max_children=MAX_CHILDREN_PER_FOLDER))
    
    def validate_no_cycle(self, node_id: str, target_parent_id: str) -> None:
        """Validate that moving node to target won't create a cycle."""
        if node_id == target_parent_id:
            raise ValueError("Move would create a cycle")
        
        # Check if target_parent_id is a descendant of node_id
        current = target_parent_id
        visited = set()
        
        while current and current not in visited:
            visited.add(current)
            if current == node_id:
                raise ValueError("Move would create a cycle")
            
            current_node = self.organization_data.tree_nodes.get(current)
            if current_node:
                current = current_node.parent_id
            else:
                break


class TreePathManager:
    """Manages materialized paths for tree nodes."""
    
    def __init__(self, organization_data: OrganizationData, debug: bool = False):
        self.organization_data = organization_data
        self.debug = debug
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def calculate_path(self, parent_id: Optional[str], name: str) -> str:
        """Calculate materialized path for a node."""
        if parent_id is None:
            return f"/{name}/"
        
        parent = self.organization_data.tree_nodes.get(parent_id)
        if parent is None:
            return f"/{name}/"
        
        return f"{parent.path}{name}/"
    
    def update_paths_recursive(self, node_id: str) -> None:
        """Recursively update materialized paths for node and descendants."""
        node = self.organization_data.tree_nodes.get(node_id)
        if not node:
            return
        
        # Update this node's path
        if node.parent_id:
            parent = self.organization_data.tree_nodes.get(node.parent_id)
            if parent:
                if node.node_type == NodeType.FOLDER:
                    node.path = f"{parent.path}{node.name}/"
                else:
                    node.path = parent.path
        else:
            # Root level
            if node.node_type == NodeType.FOLDER:
                node.path = f"/{node.name}/"
            else:
                node.path = "/"
        
        # Update all children
        for child_id in node.children:
            self.update_paths_recursive(child_id)


class TreeTraverser:
    """Handles tree traversal operations."""
    
    def __init__(self, organization_data: OrganizationData, debug: bool = False):
        self.organization_data = organization_data
        self.debug = debug
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def get_root_nodes(self) -> List[str]:
        """Get all root level nodes (no parent)."""
        return [
            node_id for node_id, node in self.organization_data.tree_nodes.items()
            if node.parent_id is None
        ]
    
    def get_descendants(self, node_id: str) -> Set[str]:
        """Get all descendant node IDs recursively."""
        descendants = set()
        
        def collect_descendants(current_id: str):
            node = self.organization_data.tree_nodes.get(current_id)
            if node:
                for child_id in node.children:
                    descendants.add(child_id)
                    collect_descendants(child_id)
        
        collect_descendants(node_id)
        return descendants
    
    def get_tree_order(self) -> List[Tuple[TreeNode, int]]:
        """Get nodes in tree display order with depth levels."""
        result = []
        
        def traverse_recursive(node_id: str, depth: int):
            node = self.organization_data.tree_nodes.get(node_id)
            if not node:
                return
            
            result.append((node, depth))
            
            # Sort children: folders first, then by name
            child_nodes = []
            for child_id in node.children:
                child_node = self.organization_data.tree_nodes.get(child_id)
                if child_node:
                    child_nodes.append((child_id, child_node))
            
            # Sort by type (folders first) then by name
            child_nodes.sort(key=lambda x: (x[1].node_type.value, x[1].name.lower()))
            
            for child_id, _ in child_nodes:
                traverse_recursive(child_id, depth + 1)
        
        # Start with root nodes
        root_nodes = self.get_root_nodes()
        root_node_objects = []
        for node_id in root_nodes:
            node = self.organization_data.tree_nodes.get(node_id)
            if node:
                root_node_objects.append((node_id, node))
        
        # Sort root nodes by type then name
        root_node_objects.sort(key=lambda x: (x[1].node_type.value, x[1].name.lower()))
        
        for node_id, _ in root_node_objects:
            traverse_recursive(node_id, 0)
        
        return result


class NodeFactory:
    """Factory for creating tree nodes."""
    
    @staticmethod
    def create_folder_node(name: str, parent_id: Optional[str] = None, 
                          path: str = "", expanded: bool = True) -> TreeNode:
        """Create a new folder node."""
        return TreeNode(
            id=str(uuid.uuid4()),
            name=name.strip(),
            node_type=NodeType.FOLDER,
            parent_id=parent_id,
            children=set(),
            path=path,
            expanded=expanded
        )
    
    @staticmethod
    def create_conversation_node(conversation_id: str, name: str, 
                               parent_id: Optional[str] = None, 
                               path: str = "") -> TreeNode:
        """Create a new conversation node."""
        return TreeNode(
            id=conversation_id,
            name=name.strip(),
            node_type=NodeType.CONVERSATION,
            parent_id=parent_id,
            children=set(),
            path=path,
            expanded=False  # Conversations don't expand
        )


class TreeModifier:
    """Handles tree modification operations."""
    
    def __init__(self, organization_data: OrganizationData, 
                 validator: TreeValidator, path_manager: TreePathManager,
                 debug: bool = False):
        self.organization_data = organization_data
        self.validator = validator
        self.path_manager = path_manager
        self.debug = debug
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def add_node(self, node: TreeNode) -> None:
        """Add a node to the tree."""
        # Validate parent exists
        parent = self.validator.validate_parent_exists(node.parent_id)
        
        # Validate depth limit
        parent_path = parent.path if parent else ""
        self.validator.validate_tree_depth(parent_path)
        
        # Validate children limit
        if node.parent_id:
            self.validator.validate_children_limit(node.parent_id)
        
        # Calculate path
        node.path = self.path_manager.calculate_path(node.parent_id, node.name)
        
        # Add to tree
        self.organization_data.tree_nodes[node.id] = node
        
        # Update parent's children
        if node.parent_id:
            parent = self.organization_data.tree_nodes[node.parent_id]
            parent.children.add(node.id)
    
    def remove_node(self, node_id: str) -> Set[str]:
        """Remove a node and all its descendants. Returns set of removed IDs."""
        self.validator.validate_node_exists(node_id)
        
        # Get all descendants first
        traverser = TreeTraverser(self.organization_data, self.debug)
        descendants = traverser.get_descendants(node_id)
        all_to_remove = descendants.copy()
        all_to_remove.add(node_id)
        
        # Remove from parent's children
        node = self.organization_data.tree_nodes[node_id]
        if node.parent_id:
            parent = self.organization_data.tree_nodes.get(node.parent_id)
            if parent:
                parent.children.discard(node_id)
        
        # Remove all nodes
        for remove_id in all_to_remove:
            if remove_id in self.organization_data.tree_nodes:
                del self.organization_data.tree_nodes[remove_id]
            if remove_id in self.organization_data.conversation_metadata:
                del self.organization_data.conversation_metadata[remove_id]
        
        return all_to_remove
    
    def move_node(self, node_id: str, new_parent_id: Optional[str]) -> None:
        """Move a node to a new parent."""
        # Validate all constraints
        node = self.validator.validate_node_exists(node_id)
        new_parent = self.validator.validate_parent_exists(new_parent_id)
        
        if new_parent_id:
            self.validator.validate_no_cycle(node_id, new_parent_id)
            self.validator.validate_children_limit(new_parent_id)
            
            # Validate depth
            new_parent_path = new_parent.path if new_parent else ""
            self.validator.validate_tree_depth(new_parent_path)
        
        # Remove from old parent
        if node.parent_id:
            old_parent = self.organization_data.tree_nodes.get(node.parent_id)
            if old_parent:
                old_parent.children.discard(node_id)
        
        # Add to new parent
        if new_parent_id:
            new_parent.children.add(node_id)
        
        # Update node's parent
        node.parent_id = new_parent_id
        
        # Update paths recursively
        self.path_manager.update_paths_recursive(node_id)