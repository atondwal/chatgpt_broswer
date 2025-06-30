"""Test Claude project detection functionality."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ccsm.core.claude_loader import find_claude_project_for_cwd, encode_path_like_claude


class TestClaudeProjectDetection:
    """Tests for Claude project detection in current working directory."""

    def test_find_claude_project_for_cwd_no_projects_dir(self):
        """Test when ~/.claude/projects doesn't exist."""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path("/fake/home")
            result = find_claude_project_for_cwd()
            assert result is None

    def test_find_claude_project_for_cwd_not_in_project(self):
        """Test when current directory is not in any Claude project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create fake ~/.claude/projects
            projects_dir = temp_path / ".claude" / "projects"
            projects_dir.mkdir(parents=True)
            
            # Create a project directory
            project_dir = projects_dir / "test-project"
            project_dir.mkdir()
            
            # Create a conversation file
            conv_file = project_dir / "conv1.jsonl"
            conv_file.write_text('{"type": "user", "content": "test"}\n')
            
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = temp_path
                with patch('pathlib.Path.cwd') as mock_cwd:
                    # Set cwd to somewhere completely different
                    mock_cwd.return_value = Path("/some/other/path")
                    result = find_claude_project_for_cwd()
                    assert result is None

    def test_find_claude_project_for_cwd_exact_match(self):
        """Test when current directory is exactly a Claude project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create fake ~/.claude/projects
            projects_dir = temp_path / ".claude" / "projects"
            projects_dir.mkdir(parents=True)
            
            # Create a project directory with Claude's naming convention
            # For project path "/test/project", Claude creates "-test-project"
            project_dir = projects_dir / "-test-project"
            project_dir.mkdir()
            
            # Create a conversation file
            conv_file = project_dir / "conv1.jsonl"
            conv_file.write_text('{"type": "user", "content": "test"}\n')
            
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = temp_path
                with patch('pathlib.Path.cwd') as mock_cwd:
                    # Current directory is the original project path
                    mock_cwd.return_value = Path("/test/project")
                    result = find_claude_project_for_cwd()
                    assert result == str(project_dir.resolve())

    def test_find_claude_project_for_cwd_subdirectory(self):
        """Test when current directory is a subdirectory of a Claude project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create fake ~/.claude/projects
            projects_dir = temp_path / ".claude" / "projects"
            projects_dir.mkdir(parents=True)
            
            # Create a project directory with Claude's naming convention
            project_dir = projects_dir / "-test-project"
            project_dir.mkdir()
            
            # Create a conversation file
            conv_file = project_dir / "conv1.jsonl"
            conv_file.write_text('{"type": "user", "content": "test"}\n')
            
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = temp_path
                with patch('pathlib.Path.cwd') as mock_cwd:
                    # Current directory is a subdirectory of the original project path
                    mock_cwd.return_value = Path("/test/project/subdir/deeper")
                    result = find_claude_project_for_cwd()
                    assert result == str(project_dir.resolve())

    def test_find_claude_project_for_cwd_multiple_projects_chooses_deepest(self):
        """Test when current directory could match multiple projects, chooses the deepest."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create fake ~/.claude/projects
            projects_dir = temp_path / ".claude" / "projects"
            projects_dir.mkdir(parents=True)
            
            # Create nested project structure with Claude naming
            parent_project = projects_dir / "-parent-project"
            parent_project.mkdir()
            
            child_project = projects_dir / "-parent-project-child"
            child_project.mkdir()
            
            # Create conversation files
            (parent_project / "conv1.jsonl").write_text('{"type": "user", "content": "test"}\n')
            (child_project / "conv2.jsonl").write_text('{"type": "user", "content": "test"}\n')
            
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = temp_path
                with patch('pathlib.Path.cwd') as mock_cwd:
                    # Current directory that would match both projects
                    mock_cwd.return_value = Path("/parent/project/child/src")
                    result = find_claude_project_for_cwd()
                    # Should choose the deeper/longer path match
                    assert result == str(child_project.resolve())

    def test_find_claude_project_for_cwd_empty_project_dir(self):
        """Test when project directory exists but has no conversations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create fake ~/.claude/projects
            projects_dir = temp_path / ".claude" / "projects"
            projects_dir.mkdir(parents=True)
            
            # Create empty project directory with Claude naming
            project_dir = projects_dir / "-empty-project"
            project_dir.mkdir()
            
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = temp_path
                with patch('pathlib.Path.cwd') as mock_cwd:
                    mock_cwd.return_value = Path("/empty/project")
                    result = find_claude_project_for_cwd()
                    # Should still return the project even if empty
                    assert result == str(project_dir.resolve())

    def test_encode_path_like_claude(self):
        """Test that path encoding matches Claude's encoding scheme."""
        # Test basic path encoding
        assert encode_path_like_claude(Path("/home/user/project")) == "-home-user-project"
        
        # Test path with underscores (converted to dashes)
        assert encode_path_like_claude(Path("/home/user/my_project")) == "-home-user-my-project"
        
        # Test path with spaces (converted to dashes)
        assert encode_path_like_claude(Path("/home/user/my project")) == "-home-user-my-project"
        
        # Test path with mixed special characters
        assert encode_path_like_claude(Path("/home/user/my_cool-project")) == "-home-user-my-cool-project"
        
        # Test path with dots and other special chars
        assert encode_path_like_claude(Path("/home/user/project.v2")) == "-home-user-project-v2"
        
        # Test path with multiple consecutive special chars
        assert encode_path_like_claude(Path("/home/user/my___project")) == "-home-user-my-project"
        
        # Test path with trailing special chars
        assert encode_path_like_claude(Path("/home/user/project_")) == "-home-user-project"
        
        # Test single directory
        assert encode_path_like_claude(Path("/project")) == "-project"
        
        # Test root directory
        assert encode_path_like_claude(Path("/")) == "-"
        
        # Test complex real-world example
        assert encode_path_like_claude(Path("/home/user/my-app_v2.0 (dev)")) == "-home-user-my-app-v2-0-dev"

    def test_find_claude_project_with_underscores(self):
        """Test project detection works with underscores in directory names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create fake ~/.claude/projects
            projects_dir = temp_path / ".claude" / "projects"
            projects_dir.mkdir(parents=True)
            
            # Create project directory with underscores (as Claude would encode it)
            # Note: underscores are now converted to dashes in the new encoding
            project_dir = projects_dir / "-home-user-my-awesome-project"
            project_dir.mkdir()
            
            # Create a conversation file
            conv_file = project_dir / "conv1.jsonl"
            conv_file.write_text('{"type": "user", "content": "test"}\n')
            
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = temp_path
                with patch('pathlib.Path.cwd') as mock_cwd:
                    # Test exact match
                    mock_cwd.return_value = Path("/home/user/my_awesome_project")
                    result = find_claude_project_for_cwd()
                    assert result == str(project_dir.resolve())
                    
                    # Test subdirectory match
                    mock_cwd.return_value = Path("/home/user/my_awesome_project/src/components")
                    result = find_claude_project_for_cwd()
                    assert result == str(project_dir.resolve())

    def test_find_claude_project_with_various_special_chars(self):
        """Test project detection works with various special characters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create fake ~/.claude/projects
            projects_dir = temp_path / ".claude" / "projects"
            projects_dir.mkdir(parents=True)
            
            # Create project directories with various special characters (as Claude would encode them)
            test_cases = [
                ("/home/user/my project", "-home-user-my-project"),
                ("/home/user/app.v2", "-home-user-app-v2"),
                ("/home/user/my_app_v2", "-home-user-my-app-v2"),
                ("/home/user/project (dev)", "-home-user-project-dev"),
            ]
            
            for original_path, encoded_name in test_cases:
                project_dir = projects_dir / encoded_name
                project_dir.mkdir()
                
                # Create a conversation file
                conv_file = project_dir / "conv1.jsonl"
                conv_file.write_text('{"type": "user", "content": "test"}\n')
                
                with patch('pathlib.Path.home') as mock_home:
                    mock_home.return_value = temp_path
                    with patch('pathlib.Path.cwd') as mock_cwd:
                        # Test exact match
                        mock_cwd.return_value = Path(original_path)
                        result = find_claude_project_for_cwd()
                        assert result == str(project_dir.resolve()), f"Failed for {original_path} -> {encoded_name}"