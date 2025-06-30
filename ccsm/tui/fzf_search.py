#!/usr/bin/env python3
"""FZF integration for fuzzy search functionality."""

import subprocess
import tempfile
import os
from typing import List, Tuple, Optional, Any
from ccsm.tree.tree import TreeNode
from ccsm.core.models import Conversation


class FZFSearch:
    """External FZF integration for fuzzy search."""
    
    def __init__(self):
        self.fzf_available = self._check_fzf_available()
        
    def _check_fzf_available(self) -> bool:
        """Check if fzf is available on the system."""
        try:
            subprocess.run(['fzf', '--version'], 
                         capture_output=True, check=True, timeout=2)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def is_available(self) -> bool:
        """Check if FZF is available for use."""
        return self.fzf_available
    
    def search_conversations(self, tree_items: List[Tuple[TreeNode, Optional[Conversation], int]]) -> Optional[int]:
        """
        Launch FZF to search through conversations and return selected index.
        
        Args:
            tree_items: List of (TreeNode, Conversation, depth) tuples
            
        Returns:
            Selected tree item index, or None if cancelled/error
        """
        if not self.fzf_available:
            return None
            
        # Prepare search data
        search_lines = []
        index_map = {}  # Maps line number to tree_items index
        
        for i, (node, conv, depth) in enumerate(tree_items):
            if not node.is_folder and conv:  # Only include conversations, not folders
                # Format: "title | created | modified | messages"
                from ccsm.core.time_utils import format_relative_time
                # Convert datetime to timestamp if needed
                create_ts = conv.create_time.timestamp() if hasattr(conv.create_time, 'timestamp') else conv.create_time
                update_ts = conv.update_time.timestamp() if hasattr(conv.update_time, 'timestamp') else conv.update_time
                created = format_relative_time(create_ts)
                modified = format_relative_time(update_ts)
                msg_count = len(conv.messages) if conv.messages else 0
                
                # Create searchable line with metadata
                search_line = f"{conv.title} | {created} | {modified} | {msg_count} msgs"
                search_lines.append(search_line)
                index_map[len(search_lines) - 1] = i
        
        if not search_lines:
            return None
            
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write('\n'.join(search_lines))
            temp_file = f.name
        
        try:
            # Launch FZF with enhanced options
            fzf_cmd = [
                'fzf',
                '--prompt=🔍 Search conversations: ',
                '--height=60%',
                '--layout=reverse',
                '--border',
                '--info=inline',
                '--preview-window=right:50%:wrap',
                '--preview=echo {}',
                '--bind=ctrl-j:down,ctrl-k:up',
                '--bind=ctrl-d:page-down,ctrl-u:page-up',
                '--color=fg:#d0d0d0,bg:#121212,hl:#5f87af',
                '--color=fg+:#d0d0d0,bg+:#262626,hl+:#5fd7ff',
                '--color=info:#afaf87,prompt:#d7005f,pointer:#af5fff',
                '--color=marker:#87ff00,spinner:#af5fff,header:#87afaf'
            ]
            
            result = subprocess.run(
                fzf_cmd,
                input='\n'.join(search_lines),
                text=True,
                capture_output=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Find which line was selected
                selected_line = result.stdout.strip()
                for line_idx, line in enumerate(search_lines):
                    if line == selected_line:
                        return index_map.get(line_idx)
                        
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, KeyboardInterrupt, Exception):
            pass
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except OSError:
                pass
                
        return None
    
    def search_all_items(self, tree_items: List[Tuple[TreeNode, Optional[Conversation], int]]) -> Optional[int]:
        """
        Launch FZF to search through all tree items (folders + conversations).
        
        Args:
            tree_items: List of (TreeNode, Conversation, depth) tuples
            
        Returns:
            Selected tree item index, or None if cancelled/error
        """
        if not self.fzf_available:
            return None
            
        # Prepare search data with hierarchy
        search_lines = []
        
        for i, (node, conv, depth) in enumerate(tree_items):
            # Create indentation to show hierarchy
            indent = "  " * depth
            
            if node.is_folder:
                # Folder entry
                icon = "📁"
                child_count = len(node.children) if hasattr(node, 'children') else 0
                search_line = f"{indent}{icon} {node.name} ({child_count} items)"
            else:
                # Conversation entry
                icon = "💬"
                if conv:
                    from ccsm.core.time_utils import format_relative_time
                    # Convert datetime to timestamp if needed
                    update_ts = conv.update_time.timestamp() if hasattr(conv.update_time, 'timestamp') else conv.update_time
                    modified = format_relative_time(update_ts)
                    msg_count = len(conv.messages) if conv.messages else 0
                    search_line = f"{indent}{icon} {conv.title} | {modified} | {msg_count} msgs"
                else:
                    search_line = f"{indent}{icon} {node.name}"
            
            search_lines.append(search_line)
        
        if not search_lines:
            return None
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write('\n'.join(search_lines))
            temp_file = f.name
        
        try:
            # Launch FZF for all items
            fzf_cmd = [
                'fzf',
                '--prompt=🌳 Search tree: ',
                '--height=60%',
                '--layout=reverse',
                '--border',
                '--info=inline',
                '--preview-window=right:40%:wrap',
                '--preview=echo {}',
                '--bind=ctrl-j:down,ctrl-k:up',
                '--bind=ctrl-d:page-down,ctrl-u:page-up',
                '--color=fg:#d0d0d0,bg:#121212,hl:#5f87af',
                '--color=fg+:#d0d0d0,bg+:#262626,hl+:#5fd7ff',
                '--color=info:#afaf87,prompt:#d7005f,pointer:#af5fff',
                '--color=marker:#87ff00,spinner:#af5fff,header:#87afaf'
            ]
            
            result = subprocess.run(
                fzf_cmd,
                input='\n'.join(search_lines),
                text=True,
                capture_output=True,
                timeout=300
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Find which line was selected
                selected_line = result.stdout.strip()
                for line_idx, line in enumerate(search_lines):
                    if line == selected_line:
                        return line_idx
                        
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, KeyboardInterrupt, Exception):
            pass
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except OSError:
                pass
                
        return None
    
    def get_installation_message(self) -> str:
        """Get message about FZF installation."""
        return ("FZF not found. Install with: brew install fzf (Mac) or "
                "apt install fzf (Ubuntu) or visit https://github.com/junegunn/fzf")