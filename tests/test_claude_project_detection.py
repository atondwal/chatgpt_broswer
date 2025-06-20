"""Test Claude project detection functionality."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from chatgpt_browser.core.claude_loader import find_claude_project_for_cwd


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