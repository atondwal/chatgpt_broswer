#!/usr/bin/env python3
"""Simple, self-documenting conversation tree."""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class TreeNode:
    """A node in the tree - either a folder or conversation."""
    def __init__(self, id: str, name: str, is_folder: bool, parent_id: Optional[str] = None):
        self.id = id
        self.name = name
        self.is_folder = is_folder
        self.parent_id = parent_id
        self.children: Set[str] = set()
        self.expanded = True


class ConversationTree:
    """Organizes conversations into a folder hierarchy."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.org_filename = filename.replace('.json', '_organization.json')
        self.nodes: Dict[str, TreeNode] = {}  # All nodes (folders and conversations)
        self.root_nodes: Set[str] = set()      # Top-level node IDs
        self.metadata: Dict[str, dict] = {}    # Extra data for conversations
        self.custom_order: Dict[str, List[str]] = {}  # Custom ordering for each parent
        self._load()
    
    def _load(self) -> None:
        """Load tree from disk."""
        org_path = Path(self.org_filename)
        if not org_path.exists():
            return
            
        try:
            with open(org_path) as f:
                data = json.load(f)
                
            # Recreate nodes
            for node_data in data.get('nodes', []):
                node = TreeNode(
                    id=node_data['id'],
                    name=node_data['name'],
                    is_folder=node_data['is_folder'],
                    parent_id=node_data.get('parent_id')
                )
                node.children = set(node_data.get('children', []))
                node.expanded = node_data.get('expanded', True)
                self.nodes[node.id] = node
                
            self.root_nodes = set(data.get('root_nodes', []))
            self.metadata = data.get('metadata', {})
            self.custom_order = data.get('custom_order', {})
            
            # Clean up any invalid references
            self._clean_invalid_references()
        except Exception:
            # If loading fails, start fresh
            pass
    
    def _clean_invalid_references(self) -> None:
        """Remove invalid node references."""
        # Clean root_nodes
        self.root_nodes = {id for id in self.root_nodes if id in self.nodes}
        
        # Clean children references
        for node in self.nodes.values():
            node.children = {id for id in node.children if id in self.nodes}
            
        # Fix parent references
        for node in self.nodes.values():
            if node.parent_id and node.parent_id not in self.nodes:
                node.parent_id = None
                self.root_nodes.add(node.id)
    
    def save(self) -> None:
        """Save tree to disk."""
        data = {
            'nodes': [
                {
                    'id': node.id,
                    'name': node.name,
                    'is_folder': node.is_folder,
                    'parent_id': node.parent_id,
                    'children': list(node.children),
                    'expanded': node.expanded
                }
                for node in self.nodes.values()
            ],
            'root_nodes': list(self.root_nodes),
            'metadata': self.metadata,
            'custom_order': self.custom_order
        }
        
        # Write to temp file first for safety
        temp_path = Path(self.org_filename + '.tmp')
        with open(temp_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Move temp to real file
        temp_path.replace(self.org_filename)
    
    def create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """Create a new folder."""
        folder_id = str(uuid.uuid4())
        folder = TreeNode(folder_id, name, is_folder=True, parent_id=parent_id)
        self.nodes[folder_id] = folder
        
        if parent_id:
            if parent_id in self.nodes:
                self.nodes[parent_id].children.add(folder_id)
        else:
            self.root_nodes.add(folder_id)
            
        return folder_id
    
    def add_conversation(self, conv_id: str, title: str, parent_id: Optional[str] = None) -> None:
        """Add a conversation to the tree."""
        if conv_id in self.nodes:
            return  # Already in tree
            
        node = TreeNode(conv_id, title, is_folder=False, parent_id=parent_id)
        self.nodes[conv_id] = node
        
        if parent_id and parent_id in self.nodes:
            self.nodes[parent_id].children.add(conv_id)
        else:
            self.root_nodes.add(conv_id)
    
    def move_node(self, node_id: str, new_parent_id: Optional[str]) -> None:
        """Move a node to a different parent."""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")
            
        node = self.nodes[node_id]
        old_parent_id = node.parent_id
        
        # Remove from old parent
        if old_parent_id and old_parent_id in self.nodes:
            self.nodes[old_parent_id].children.discard(node_id)
        else:
            self.root_nodes.discard(node_id)
        
        # Add to new parent
        node.parent_id = new_parent_id
        if new_parent_id and new_parent_id in self.nodes:
            self.nodes[new_parent_id].children.add(node_id)
        else:
            self.root_nodes.add(node_id)
    
    def delete_node(self, node_id: str) -> None:
        """Delete a node and all its children."""
        if node_id not in self.nodes:
            return
            
        # Get all descendants
        to_delete = [node_id]
        i = 0
        while i < len(to_delete):
            current = to_delete[i]
            if current in self.nodes:
                to_delete.extend(self.nodes[current].children)
            i += 1
        
        # Remove from parents
        for del_id in to_delete:
            if del_id in self.nodes:
                node = self.nodes[del_id]
                if node.parent_id and node.parent_id in self.nodes:
                    self.nodes[node.parent_id].children.discard(del_id)
                else:
                    self.root_nodes.discard(del_id)
                del self.nodes[del_id]
    
    def get_tree_items(self, conversations: List[any], sort_by_date: bool = True, use_custom_order: bool = True) -> List[Tuple[TreeNode, Optional[any], int]]:
        """Get all items in tree order for display."""
        # Create lookup for conversations
        conv_map = {c.id: c for c in conversations}
        
        # Add all conversations to tree if not already there
        for conv in conversations:
            if conv.id not in self.nodes:
                self.add_conversation(conv.id, conv.title)
        
        # Build tree recursively
        items = []
        
        def add_children(node_ids: Set[str], depth: int = 0, parent_id: Optional[str] = None):
            # Filter out non-existent nodes
            valid_ids = [id for id in node_ids if id in self.nodes]
            
            # Check if we have custom ordering for this parent
            custom_key = parent_id or "root"
            if use_custom_order and custom_key in self.custom_order:
                # Use custom order, but include any new items at the end
                custom_ordered = self.custom_order[custom_key]
                ordered_ids = []
                
                # Add items in custom order if they exist
                for item_id in custom_ordered:
                    if item_id in valid_ids:
                        ordered_ids.append(item_id)
                        
                # Add any new items not in custom order
                for item_id in valid_ids:
                    if item_id not in custom_ordered:
                        ordered_ids.append(item_id)
                        
                sorted_ids = ordered_ids
            else:
                # Use automatic sorting
                # Separate folders and conversations
                folder_ids = [id for id in valid_ids if self.nodes[id].is_folder]
                conv_ids = [id for id in valid_ids if not self.nodes[id].is_folder]
                
                # Sort folders by name
                folder_ids.sort(key=lambda id: self.nodes[id].name.lower())
                
                # Filter out conversations not in the filtered set
                conv_ids = [id for id in conv_ids if id in conv_map]
                
                # Sort conversations by date (newest first) or name
                if sort_by_date:
                    conv_ids.sort(key=lambda id: conv_map.get(id).create_time or 0, reverse=True)
                else:
                    conv_ids.sort(key=lambda id: self.nodes[id].name.lower())
                
                # Combine: folders first, then conversations
                sorted_ids = folder_ids + conv_ids
            
            for node_id in sorted_ids:
                    
                node = self.nodes[node_id]
                if node.is_folder:
                    items.append((node, None, depth))
                    if node.expanded:
                        add_children(node.children, depth + 1, node_id)
                else:
                    conv = conv_map.get(node_id)
                    # Only show conversations that are in the filtered set
                    if conv is not None:
                        items.append((node, conv, depth))
        
        add_children(self.root_nodes, 0, None)
        return items
    
    def rename_node(self, node_id: str, new_name: str) -> None:
        """Rename a node."""
        if node_id in self.nodes:
            self.nodes[node_id].name = new_name
    
    def toggle_folder(self, node_id: str) -> None:
        """Toggle folder expansion state."""
        if node_id in self.nodes and self.nodes[node_id].is_folder:
            self.nodes[node_id].expanded = not self.nodes[node_id].expanded
    
    def update_metadata(self, conv_id: str, **kwargs) -> None:
        """Update conversation metadata."""
        if conv_id not in self.metadata:
            self.metadata[conv_id] = {}
        self.metadata[conv_id].update(kwargs)
    
    def move_item_up(self, item_id: str) -> bool:
        """Move an item up within its parent's children list."""
        if item_id not in self.nodes:
            return False
            
        node = self.nodes[item_id]
        parent_key = node.parent_id or "root"
        
        # Get current order for this parent  
        if parent_key not in self.custom_order:
            # Initialize from siblings in deterministic order (folders first, then by name)
            if node.parent_id:
                if node.parent_id not in self.nodes:
                    return False
                siblings = self.nodes[node.parent_id].children
            else:
                siblings = self.root_nodes
                
            # Create deterministic order: folders first (by name), then conversations (by name)
            siblings_list = list(siblings)
            folder_ids = [id for id in siblings_list if id in self.nodes and self.nodes[id].is_folder]
            conv_ids = [id for id in siblings_list if id in self.nodes and not self.nodes[id].is_folder]
            
            folder_ids.sort(key=lambda id: self.nodes[id].name.lower())
            conv_ids.sort(key=lambda id: self.nodes[id].name.lower())
            
            self.custom_order[parent_key] = folder_ids + conv_ids
            
        order = self.custom_order[parent_key]
        
        if item_id not in order:
            order.append(item_id)
            
        # Find current position
        current_idx = order.index(item_id)
        if current_idx == 0:
            return False  # Already at top
            
        # Swap with previous item
        order[current_idx], order[current_idx - 1] = order[current_idx - 1], order[current_idx]
        
        return True
    
    def move_item_down(self, item_id: str) -> bool:
        """Move an item down within its parent's children list."""
        if item_id not in self.nodes:
            return False
            
        node = self.nodes[item_id]
        parent_key = node.parent_id or "root"
        
        # Get current order for this parent
        if parent_key not in self.custom_order:
            # Initialize from siblings in deterministic order (folders first, then by name)
            if node.parent_id:
                if node.parent_id not in self.nodes:
                    return False
                siblings = self.nodes[node.parent_id].children
            else:
                siblings = self.root_nodes
                
            # Create deterministic order: folders first (by name), then conversations (by name)
            siblings_list = list(siblings)
            folder_ids = [id for id in siblings_list if id in self.nodes and self.nodes[id].is_folder]
            conv_ids = [id for id in siblings_list if id in self.nodes and not self.nodes[id].is_folder]
            
            folder_ids.sort(key=lambda id: self.nodes[id].name.lower())
            conv_ids.sort(key=lambda id: self.nodes[id].name.lower())
            
            self.custom_order[parent_key] = folder_ids + conv_ids
            
        order = self.custom_order[parent_key]
        
        if item_id not in order:
            order.append(item_id)
            
        # Find current position
        current_idx = order.index(item_id)
        if current_idx == len(order) - 1:
            return False  # Already at bottom
            
        # Swap with next item
        order[current_idx], order[current_idx + 1] = order[current_idx + 1], order[current_idx]
        
        return True