#!/usr/bin/env python3
"""
ChatGPT Conversation Tree Organization

Implements hierarchical organization of ChatGPT conversations with folders,
metadata, and efficient tree operations using adjacency list + materialized paths.

Author: Generated with Claude Code
"""

# Standard library imports
import json
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

# Third-party imports
# (none currently)

# Local imports
from src.core.chatgpt_browser import Conversation
from src.tree.tree_constants import (
    DEFAULT_SCHEMA_VERSION, BACKUP_FILE_SUFFIX, TEMP_FILE_SUFFIX,
    ERROR_MESSAGES, MAX_TREE_DEPTH, MAX_CHILDREN_PER_FOLDER
)
from src.tree.tree_types import (
    NodeType, TreeNode, ConversationMetadata, OrganizationData,
    TreeOrderResult, FilePath
)
from src.tree.tree_operations import (
    TreeValidator, TreePathManager, TreeTraverser, NodeFactory, TreeModifier
)


class TreeManager:
    """Manages tree operations with adjacency list + materialized paths."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.organization_data = OrganizationData()
        
    def create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """
        Create a new folder node.
        
        Args:
            name: Display name for the folder
            parent_id: Parent folder ID (None for root level)
            
        Returns:
            ID of the created folder
            
        Raises:
            ValueError: If parent doesn't exist or would create cycle
        """
        if not name.strip():
            raise ValueError(ERROR_MESSAGES["EMPTY_FOLDER_NAME"])
            
        # Validate parent exists if specified
        if parent_id and parent_id not in self.organization_data.tree_nodes:
            raise ValueError(ERROR_MESSAGES["PARENT_NOT_FOUND"].format(parent_id=parent_id))
            
        # Validate parent is a folder
        if parent_id:
            parent_node = self.organization_data.tree_nodes[parent_id]
            if parent_node.node_type != NodeType.FOLDER:
                raise ValueError(ERROR_MESSAGES["PARENT_NOT_FOLDER"])
            
            # Validate children limit
            if len(parent_node.children) >= MAX_CHILDREN_PER_FOLDER:
                raise ValueError(ERROR_MESSAGES["MAX_CHILDREN_EXCEEDED"].format(max_children=MAX_CHILDREN_PER_FOLDER))
            
            # Validate tree depth
            parent_path = parent_node.path
            depth = parent_path.count('/') - 1  # Count depth from parent path
            if depth >= MAX_TREE_DEPTH:
                raise ValueError(ERROR_MESSAGES["MAX_DEPTH_EXCEEDED"].format(max_depth=MAX_TREE_DEPTH))
        
        # Generate unique ID
        folder_id = str(uuid.uuid4())
        
        # Calculate path
        if parent_id:
            parent_path = self.organization_data.tree_nodes[parent_id].path
            path = f"{parent_path}{name}/"
        else:
            path = f"/{name}/"
            
        # Create folder node
        folder_node = TreeNode(
            id=folder_id,
            name=name,
            node_type=NodeType.FOLDER,
            parent_id=parent_id,
            path=path
        )
        
        # Add to data structure
        self.organization_data.tree_nodes[folder_id] = folder_node
        
        # Update parent's children
        if parent_id:
            self.organization_data.tree_nodes[parent_id].children.add(folder_id)
        else:
            self.organization_data.root_nodes.add(folder_id)
            
        self.logger.info(f"Created folder '{name}' with ID {folder_id}")
        return folder_id
        
    def move_node(self, node_id: str, new_parent_id: Optional[str]) -> None:
        """
        Move a node to a new parent.
        
        Args:
            node_id: ID of node to move
            new_parent_id: New parent ID (None for root level)
            
        Raises:
            ValueError: If node doesn't exist, would create cycle, or invalid parent
        """
        if node_id not in self.organization_data.tree_nodes:
            raise ValueError(ERROR_MESSAGES["NODE_NOT_FOUND"].format(node_id=node_id))
            
        # Validate new parent exists if specified
        if new_parent_id and new_parent_id not in self.organization_data.tree_nodes:
            raise ValueError(f"New parent {new_parent_id} does not exist")
            
        # Validate new parent is a folder
        if new_parent_id:
            parent_node = self.organization_data.tree_nodes[new_parent_id]
            if parent_node.node_type != NodeType.FOLDER:
                raise ValueError("New parent must be a folder")
        
        # Prevent moving node to itself or its descendants (cycle detection)
        if new_parent_id == node_id:
            raise ValueError(ERROR_MESSAGES["CYCLE_DETECTED"])
            
        if new_parent_id and self._would_create_cycle(node_id, new_parent_id):
            raise ValueError(ERROR_MESSAGES["CYCLE_DETECTED"])
            
        node = self.organization_data.tree_nodes[node_id]
        old_parent_id = node.parent_id
        
        # Remove from old parent
        if old_parent_id:
            self.organization_data.tree_nodes[old_parent_id].children.discard(node_id)
        else:
            self.organization_data.root_nodes.discard(node_id)
            
        # Add to new parent
        if new_parent_id:
            self.organization_data.tree_nodes[new_parent_id].children.add(node_id)
        else:
            self.organization_data.root_nodes.add(node_id)
            
        # Update node's parent
        node.parent_id = new_parent_id
        
        # Update materialized paths for node and all descendants
        self._update_paths(node_id)
        
        self.logger.info(f"Moved node {node_id} from {old_parent_id} to {new_parent_id}")
        
    def delete_node(self, node_id: str) -> None:
        """
        Delete a node and all its descendants.
        
        Args:
            node_id: ID of node to delete
            
        Raises:
            ValueError: If node doesn't exist
        """
        if node_id not in self.organization_data.tree_nodes:
            raise ValueError(ERROR_MESSAGES["NODE_NOT_FOUND"].format(node_id=node_id))
            
        # Collect all descendants first
        descendants = self._get_all_descendants(node_id)
        descendants.append(node_id)  # Include the node itself
        
        # Remove from parent
        node = self.organization_data.tree_nodes[node_id]
        if node.parent_id:
            self.organization_data.tree_nodes[node.parent_id].children.discard(node_id)
        else:
            self.organization_data.root_nodes.discard(node_id)
            
        # Delete all descendants and the node
        for desc_id in descendants:
            desc_node = self.organization_data.tree_nodes[desc_id]
            
            # Remove conversation metadata if it's a conversation node
            if desc_node.node_type == NodeType.CONVERSATION:
                self.organization_data.conversation_metadata.pop(desc_id, None)
                
            # Remove from tree
            del self.organization_data.tree_nodes[desc_id]
            
        self.logger.info(f"Deleted node {node_id} and {len(descendants) - 1} descendants")
        
    def add_conversation(self, conversation_id: str, parent_id: Optional[str] = None,
                        custom_title: Optional[str] = None) -> None:
        """
        Add a conversation to the tree.
        
        Args:
            conversation_id: ID of the conversation
            parent_id: Parent folder ID (None for root level)
            custom_title: Custom display title (uses conversation title if None)
            
        Raises:
            ValueError: If conversation already exists or parent invalid
        """
        if conversation_id in self.organization_data.tree_nodes:
            raise ValueError(f"Conversation {conversation_id} already exists in tree")
            
        # Validate parent exists if specified
        if parent_id and parent_id not in self.organization_data.tree_nodes:
            raise ValueError(ERROR_MESSAGES["PARENT_NOT_FOUND"].format(parent_id=parent_id))
            
        # Validate parent is a folder
        if parent_id:
            parent_node = self.organization_data.tree_nodes[parent_id]
            if parent_node.node_type != NodeType.FOLDER:
                raise ValueError(ERROR_MESSAGES["PARENT_NOT_FOLDER"])
            
            # Validate children limit
            if len(parent_node.children) >= MAX_CHILDREN_PER_FOLDER:
                raise ValueError(ERROR_MESSAGES["MAX_CHILDREN_EXCEEDED"].format(max_children=MAX_CHILDREN_PER_FOLDER))
        
        # Calculate path
        if parent_id:
            parent_path = self.organization_data.tree_nodes[parent_id].path
            path = f"{parent_path}{conversation_id}"
        else:
            path = f"/{conversation_id}"
            
        # Create conversation node
        conv_node = TreeNode(
            id=conversation_id,
            name=custom_title or conversation_id,  # Will be updated with actual title later
            node_type=NodeType.CONVERSATION,
            parent_id=parent_id,
            path=path
        )
        
        # Create metadata
        metadata = ConversationMetadata(
            conversation_id=conversation_id,
            custom_title=custom_title
        )
        
        # Add to data structure
        self.organization_data.tree_nodes[conversation_id] = conv_node
        self.organization_data.conversation_metadata[conversation_id] = metadata
        
        # Update parent's children
        if parent_id:
            self.organization_data.tree_nodes[parent_id].children.add(conversation_id)
        else:
            self.organization_data.root_nodes.add(conversation_id)
            
        self.logger.info(f"Added conversation {conversation_id} to tree")
        
    def get_tree_order(self) -> List[TreeNode]:
        """
        Get nodes in depth-first order for rendering.
        
        Returns:
            List of TreeNode objects in tree order
        """
        result = []
        
        # Sort root nodes by name for consistent ordering
        sorted_roots = sorted(self.organization_data.root_nodes, 
                            key=lambda nid: self.organization_data.tree_nodes[nid].name.lower())
        
        for root_id in sorted_roots:
            self._collect_tree_order(root_id, result)
            
        return result
        
    def get_node_ancestors(self, node_id: str) -> List[TreeNode]:
        """
        Get all ancestors of a node from root to parent.
        
        Args:
            node_id: ID of the node
            
        Returns:
            List of ancestor nodes from root to immediate parent
        """
        ancestors = []
        current_id = node_id
        
        while current_id in self.organization_data.tree_nodes:
            node = self.organization_data.tree_nodes[current_id]
            if node.parent_id:
                parent = self.organization_data.tree_nodes[node.parent_id]
                ancestors.insert(0, parent)
                current_id = node.parent_id
            else:
                break
                
        return ancestors
        
    def update_conversation_metadata(self, conversation_id: str, **kwargs) -> None:
        """
        Update conversation metadata.
        
        Args:
            conversation_id: ID of the conversation
            **kwargs: Metadata fields to update
        """
        if conversation_id not in self.organization_data.conversation_metadata:
            raise ValueError(f"Conversation {conversation_id} not found")
            
        metadata = self.organization_data.conversation_metadata[conversation_id]
        
        # Update allowed fields
        if 'custom_title' in kwargs:
            metadata.custom_title = kwargs['custom_title']
            # Also update the tree node name
            if conversation_id in self.organization_data.tree_nodes:
                self.organization_data.tree_nodes[conversation_id].name = kwargs['custom_title']
                
        if 'tags' in kwargs:
            metadata.tags = set(kwargs['tags']) if kwargs['tags'] else set()
            
        if 'notes' in kwargs:
            metadata.notes = kwargs['notes'] or ""
            
        if 'favorite' in kwargs:
            metadata.favorite = bool(kwargs['favorite'])
            
        self.logger.info(f"Updated metadata for conversation {conversation_id}")
        
    def _would_create_cycle(self, node_id: str, new_parent_id: str) -> bool:
        """Check if moving node to new_parent would create a cycle."""
        current_id = new_parent_id
        visited = set()
        
        while current_id and current_id not in visited:
            if current_id == node_id:
                return True
            visited.add(current_id)
            current_node = self.organization_data.tree_nodes.get(current_id)
            current_id = current_node.parent_id if current_node else None
            
        return False
        
    def _update_paths(self, node_id: str) -> None:
        """Update materialized paths for node and all descendants."""
        if node_id not in self.organization_data.tree_nodes:
            return
            
        node = self.organization_data.tree_nodes[node_id]
        
        # Calculate new path
        if node.parent_id:
            parent_path = self.organization_data.tree_nodes[node.parent_id].path
            if node.node_type == NodeType.FOLDER:
                node.path = f"{parent_path}{node.name}/"
            else:
                node.path = f"{parent_path}{node.id}"
        else:
            if node.node_type == NodeType.FOLDER:
                node.path = f"/{node.name}/"
            else:
                node.path = f"/{node.id}"
                
        # Recursively update children
        for child_id in node.children:
            self._update_paths(child_id)
            
    def _get_all_descendants(self, node_id: str) -> List[str]:
        """Get all descendant node IDs."""
        descendants = []
        
        if node_id in self.organization_data.tree_nodes:
            node = self.organization_data.tree_nodes[node_id]
            for child_id in node.children:
                descendants.append(child_id)
                descendants.extend(self._get_all_descendants(child_id))
                
        return descendants
        
    def _collect_tree_order(self, node_id: str, result: List[TreeNode]) -> None:
        """Recursively collect nodes in depth-first order."""
        if node_id not in self.organization_data.tree_nodes:
            return
            
        node = self.organization_data.tree_nodes[node_id]
        result.append(node)
        
        # Sort children by name for consistent ordering
        sorted_children = sorted(node.children, 
                               key=lambda cid: self.organization_data.tree_nodes[cid].name.lower())
        
        for child_id in sorted_children:
            self._collect_tree_order(child_id, result)


class MetadataStore:
    """Handles JSON persistence with atomic writes and backup/recovery."""
    
    def __init__(self, file_path: Union[str, Path], debug: bool = False):
        self.file_path = Path(file_path)
        self.backup_path = self.file_path.with_suffix(self.file_path.suffix + '.bak')
        self.debug = debug
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    def load(self) -> OrganizationData:
        """
        Load organization data from file.
        
        Returns:
            OrganizationData object (empty if file doesn't exist)
        """
        if not self.file_path.exists():
            self.logger.info(f"Organization file {self.file_path} doesn't exist, creating new data")
            return OrganizationData()
            
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            return self._deserialize_organization_data(data)
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.error(f"Error loading organization data: {e}")
            
            # Try to load from backup
            if self.backup_path.exists():
                self.logger.info("Attempting to load from backup")
                try:
                    with open(self.backup_path, 'r', encoding='utf-8') as f:
                        backup_data = json.load(f)
                    return self._deserialize_organization_data(backup_data)
                except Exception as backup_error:
                    self.logger.error(f"Backup also corrupted: {backup_error}")
                    
            # Return empty data if all else fails
            self.logger.warning("Creating new organization data due to corrupted files")
            return OrganizationData()
            
    def save(self, data: OrganizationData) -> None:
        """
        Save organization data to file with atomic write.
        
        Args:
            data: OrganizationData to save
        """
        try:
            # Create backup if original exists
            if self.file_path.exists():
                shutil.copy2(self.file_path, self.backup_path)
                
            # Serialize data
            serialized = self._serialize_organization_data(data)
            
            # Write to temporary file first
            temp_path = self.file_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(serialized, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
                
            # Atomic move
            temp_path.replace(self.file_path)
            
            # Create backup after successful save (if it doesn't exist yet)
            if not self.backup_path.exists():
                shutil.copy2(self.file_path, self.backup_path)
            
            self.logger.info(f"Saved organization data to {self.file_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving organization data: {e}")
            if self.debug:
                raise
                
    def _serialize_organization_data(self, data: OrganizationData) -> Dict:
        """Convert OrganizationData to JSON-serializable format."""
        return {
            'version': data.version,
            'tree_nodes': {
                node_id: {
                    'id': node.id,
                    'name': node.name,
                    'node_type': node.node_type.value,
                    'parent_id': node.parent_id,
                    'children': list(node.children),
                    'path': node.path,
                    'expanded': node.expanded
                }
                for node_id, node in data.tree_nodes.items()
            },
            'conversation_metadata': {
                conv_id: {
                    'conversation_id': meta.conversation_id,
                    'custom_title': meta.custom_title,
                    'tags': list(meta.tags),
                    'notes': meta.notes,
                    'favorite': meta.favorite
                }
                for conv_id, meta in data.conversation_metadata.items()
            },
            'root_nodes': list(data.root_nodes)
        }
        
    def _deserialize_organization_data(self, data: Dict) -> OrganizationData:
        """Convert JSON data to OrganizationData object."""
        org_data = OrganizationData()
        org_data.version = data.get('version', '1.0')
        
        # Deserialize tree nodes
        for node_id, node_data in data.get('tree_nodes', {}).items():
            node = TreeNode(
                id=node_data['id'],
                name=node_data['name'],
                node_type=NodeType(node_data['node_type']),
                parent_id=node_data.get('parent_id'),
                children=set(node_data.get('children', [])),
                path=node_data.get('path', ''),
                expanded=node_data.get('expanded', True)
            )
            org_data.tree_nodes[node_id] = node
            
        # Deserialize conversation metadata
        for conv_id, meta_data in data.get('conversation_metadata', {}).items():
            metadata = ConversationMetadata(
                conversation_id=meta_data['conversation_id'],
                custom_title=meta_data.get('custom_title'),
                tags=set(meta_data.get('tags', [])),
                notes=meta_data.get('notes', ''),
                favorite=meta_data.get('favorite', False)
            )
            org_data.conversation_metadata[conv_id] = metadata
            
        # Deserialize root nodes
        org_data.root_nodes = set(data.get('root_nodes', []))
        
        return org_data


class ConversationOrganizer:
    """Main orchestrator integrating tree management with conversation data."""
    
    def __init__(self, conversations_path: Union[str, Path], 
                 organization_path: Optional[Union[str, Path]] = None,
                 debug: bool = False):
        """
        Initialize the conversation organizer.
        
        Args:
            conversations_path: Path to conversations.json file
            organization_path: Path to organization file (auto-generated if None)
            debug: Enable debug logging
        """
        self.conversations_path = Path(conversations_path)
        self.debug = debug
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Auto-generate organization path if not provided
        if organization_path:
            self.organization_path = Path(organization_path)
        else:
            self.organization_path = self.conversations_path.with_name(
                self.conversations_path.stem + '_organization.json'
            )
            
        # Initialize components
        self.tree_manager = TreeManager(debug=debug)
        self.metadata_store = MetadataStore(self.organization_path, debug=debug)
        
        # Load existing organization data
        self.tree_manager.organization_data = self.metadata_store.load()
        
    def load_organization(self) -> OrganizationData:
        """Load current organization data."""
        return self.tree_manager.organization_data
        
    def save_organization(self) -> None:
        """Save organization data to file."""
        self.metadata_store.save(self.tree_manager.organization_data)
        
    def get_organized_conversations(self, conversations: List[Conversation]) -> List[Tuple[TreeNode, Optional[Conversation]]]:
        """
        Get conversations organized by tree structure.
        
        Args:
            conversations: List of conversation objects
            
        Returns:
            List of (TreeNode, Conversation) tuples in tree order
            TreeNode is the tree node, Conversation is None for folder nodes
        """
        
        # Create lookup for conversations by ID
        conv_lookup = {conv.id: conv for conv in conversations}
        
        # Get tree nodes in order
        tree_nodes = self.tree_manager.get_tree_order()
        
        result = []
        organized_conv_ids = set()
        
        # Add organized conversations from tree
        for node in tree_nodes:
            if node.node_type == NodeType.FOLDER:
                result.append((node, None))
            else:
                # Find matching conversation
                conv = conv_lookup.get(node.id)
                if conv:
                    # Update node name with actual conversation title if no custom title
                    metadata = self.tree_manager.organization_data.conversation_metadata.get(node.id)
                    if metadata and not metadata.custom_title:
                        node.name = conv.title
                    result.append((node, conv))
                    organized_conv_ids.add(node.id)
        
        # Add unorganized conversations at the end
        for conv in conversations:
            if conv.id not in organized_conv_ids:
                # Create a temporary node for unorganized conversation
                temp_node = TreeNode(
                    id=conv.id,
                    name=conv.title,
                    node_type=NodeType.CONVERSATION,
                    parent_id=None,
                    path="/",
                    expanded=False
                )
                result.append((temp_node, conv))
                
        return result
        
    def create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """Create a new folder. Delegates to TreeManager."""
        return self.tree_manager.create_folder(name, parent_id)
        
    def move_node(self, node_id: str, new_parent_id: Optional[str]) -> None:
        """Move a node. Delegates to TreeManager."""
        self.tree_manager.move_node(node_id, new_parent_id)
        
    def delete_node(self, node_id: str) -> None:
        """Delete a node. Delegates to TreeManager."""
        self.tree_manager.delete_node(node_id)
        
    def add_conversation(self, conversation_id: str, parent_id: Optional[str] = None,
                        custom_title: Optional[str] = None) -> None:
        """Add a conversation to the tree. Delegates to TreeManager."""
        self.tree_manager.add_conversation(conversation_id, parent_id, custom_title)
        
    def update_conversation_metadata(self, conversation_id: str, **kwargs) -> None:
        """Update conversation metadata. Delegates to TreeManager."""
        self.tree_manager.update_conversation_metadata(conversation_id, **kwargs)