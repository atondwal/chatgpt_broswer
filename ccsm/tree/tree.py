#!/usr/bin/env python3
"""Simple, self-documenting conversation tree."""

import json
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class TreeNode:
    """A node in the tree - either a folder or conversation."""
    id: str
    name: str
    is_folder: bool
    parent_id: Optional[str] = None
    children: Set[str] = field(default_factory=set)
    expanded: bool = True


class ConversationTree:
    """Organizes conversations into a folder hierarchy."""
    
    def __init__(self, filename: str):
        self.filename = filename
        
        # Handle different file types for organization file
        if filename.endswith('.json'):
            self.org_filename = filename.replace('.json', '_organization.json')
        elif filename.endswith('.jsonl'):
            self.org_filename = filename.replace('.jsonl', '_organization.json')
        else:
            # For directories (Claude projects), put org file in the directory
            import os
            if os.path.isdir(filename):
                self.org_filename = os.path.join(filename, '_organization.json')
            else:
                self.org_filename = filename + '_organization.json'
        
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
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            # If loading fails, start fresh
            logging.debug(f"Failed to load tree structure from {self.tree_file}: {e}")
    
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
        conv_map = {c.id: c for c in conversations}
        self._ensure_conversations_in_tree(conversations)
        
        items = []
        self._build_tree_items(self.root_nodes, 0, None, conv_map, sort_by_date, use_custom_order, items)
        return items
    
    def _ensure_conversations_in_tree(self, conversations: List[any]) -> None:
        """Add conversations to tree if not already present."""
        for conv in conversations:
            if conv.id not in self.nodes:
                self.add_conversation(conv.id, conv.title)
    
    def _get_sorted_children(self, node_ids: Set[str], parent_id: Optional[str], conv_map: dict, sort_by_date: bool, use_custom_order: bool) -> List[str]:
        """Get children sorted according to custom order or automatic sorting."""
        valid_ids = [id for id in node_ids if id in self.nodes]
        custom_key = parent_id or "root"
        
        if use_custom_order and custom_key in self.custom_order:
            return self._apply_custom_order(valid_ids, custom_key)
        else:
            return self._apply_automatic_sort(valid_ids, conv_map, sort_by_date)
    
    def _apply_custom_order(self, valid_ids: List[str], custom_key: str) -> List[str]:
        """Apply custom ordering to node list."""
        custom_ordered = self.custom_order[custom_key]
        ordered_ids = [id for id in custom_ordered if id in valid_ids]
        # Add any new items not in custom order
        ordered_ids.extend(id for id in valid_ids if id not in custom_ordered)
        return ordered_ids
    
    def _apply_automatic_sort(self, valid_ids: List[str], conv_map: dict, sort_by_date: bool) -> List[str]:
        """Apply automatic sorting (folders first, then conversations)."""
        folder_ids = [id for id in valid_ids if self.nodes[id].is_folder]
        conv_ids = [id for id in valid_ids if not self.nodes[id].is_folder and id in conv_map]
        
        folder_ids.sort(key=lambda id: self.nodes[id].name.lower())
        
        if sort_by_date:
            conv_ids.sort(key=lambda id: conv_map.get(id).create_time or 0, reverse=True)
        else:
            conv_ids.sort(key=lambda id: self.nodes[id].name.lower())
            
        return folder_ids + conv_ids
    
    def _build_tree_items(self, node_ids: Set[str], depth: int, parent_id: Optional[str], conv_map: dict, sort_by_date: bool, use_custom_order: bool, items: List) -> None:
        """Recursively build tree items for display."""
        sorted_ids = self._get_sorted_children(node_ids, parent_id, conv_map, sort_by_date, use_custom_order)
        
        for node_id in sorted_ids:
            node = self.nodes[node_id]
            if node.is_folder:
                items.append((node, None, depth))
                if node.expanded:
                    self._build_tree_items(node.children, depth + 1, node_id, conv_map, sort_by_date, use_custom_order, items)
            else:
                conv = conv_map.get(node_id)
                if conv is not None:
                    items.append((node, conv, depth))
    
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
    
    def _ensure_custom_order(self, parent_key: str, node: TreeNode) -> None:
        """Initialize custom order for a parent if not already set."""
        if parent_key in self.custom_order:
            return
            
        # Get siblings
        if node.parent_id:
            if node.parent_id not in self.nodes:
                return
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
    
    def move_item_up(self, item_id: str) -> bool:
        """Move an item up within its parent's children list."""
        if item_id not in self.nodes:
            return False
            
        node = self.nodes[item_id]
        parent_key = node.parent_id or "root"
        
        self._ensure_custom_order(parent_key, node)
        order = self.custom_order[parent_key]
        
        if item_id not in order:
            order.append(item_id)
            
        current_idx = order.index(item_id)
        if current_idx == 0:
            return False
            
        order[current_idx], order[current_idx - 1] = order[current_idx - 1], order[current_idx]
        return True
    
    def move_item_down(self, item_id: str) -> bool:
        """Move an item down within its parent's children list."""
        if item_id not in self.nodes:
            return False
            
        node = self.nodes[item_id]
        parent_key = node.parent_id or "root"
        
        self._ensure_custom_order(parent_key, node)
        order = self.custom_order[parent_key]
        
        if item_id not in order:
            order.append(item_id)
            
        current_idx = order.index(item_id)
        if current_idx == len(order) - 1:
            return False
            
        order[current_idx], order[current_idx + 1] = order[current_idx + 1], order[current_idx]
        return True
    
    def clear_custom_order(self) -> None:
        """Clear all custom ordering, restoring automatic sorting."""
        self.custom_order.clear()