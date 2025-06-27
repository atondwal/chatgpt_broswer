#!/usr/bin/env python3
"""Tests for input validation utilities."""

import json
import tempfile
from pathlib import Path

import pytest

from chatgpt_browser.core.validation import (
    validate_file_path, validate_json_data, validate_conversation_number,
    validate_project_selection, sanitize_search_term, validate_export_format,
    validate_count_parameter
)


class TestFilePathValidation:
    """Test file path validation functionality."""
    
    def test_validate_existing_file(self):
        """Test validation of existing file."""
        with tempfile.NamedTemporaryFile() as tmp:
            result = validate_file_path(tmp.name, must_exist=True)
            assert result is not None
            assert result.exists()
    
    def test_validate_nonexistent_file_must_exist(self):
        """Test validation fails for non-existent file when must_exist=True."""
        result = validate_file_path("/nonexistent/file.txt", must_exist=True)
        assert result is None
    
    def test_validate_nonexistent_file_optional(self):
        """Test validation succeeds for non-existent file when must_exist=False."""
        result = validate_file_path("/some/path/file.txt", must_exist=False)
        assert result is not None
        assert str(result) == "/some/path/file.txt"
    
    def test_validate_directory_with_jsonl(self):
        """Test validation of directory containing JSONL files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a JSONL file
            jsonl_file = Path(tmpdir) / "test.jsonl"
            jsonl_file.write_text('{"test": "data"}\n')
            
            result = validate_file_path(tmpdir, must_exist=True)
            assert result is not None
            assert result.is_dir()
    
    def test_validate_invalid_path(self):
        """Test validation fails for invalid path."""
        # Test with null bytes (invalid in paths)
        result = validate_file_path("path\x00with\x00nulls", must_exist=False)
        assert result is None


class TestJsonValidation:
    """Test JSON data validation functionality."""
    
    def test_validate_valid_json_object(self):
        """Test validation of valid JSON object."""
        json_str = '{"key": "value", "number": 42}'
        result = validate_json_data(json_str)
        assert result == {"key": "value", "number": 42}
    
    def test_validate_valid_json_array(self):
        """Test validation of valid JSON array."""
        json_str = '[{"item": 1}, {"item": 2}]'
        result = validate_json_data(json_str, expect_array=True)
        assert result == [{"item": 1}, {"item": 2}]
    
    def test_validate_object_when_expecting_array(self):
        """Test validation fails when expecting array but getting object."""
        json_str = '{"key": "value"}'
        result = validate_json_data(json_str, expect_array=True)
        assert result is None
    
    def test_validate_invalid_json(self):
        """Test validation fails for invalid JSON."""
        json_str = '{"invalid": json,}'
        result = validate_json_data(json_str)
        assert result is None


class TestConversationNumberValidation:
    """Test conversation number validation functionality."""
    
    def test_validate_valid_number(self):
        """Test validation of valid conversation number."""
        result = validate_conversation_number("5", 10)
        assert result == 5
    
    def test_validate_number_too_low(self):
        """Test validation fails for number too low."""
        result = validate_conversation_number("0", 10)
        assert result is None
        
        result = validate_conversation_number("-1", 10)
        assert result is None
    
    def test_validate_number_too_high(self):
        """Test validation fails for number too high."""
        result = validate_conversation_number("15", 10)
        assert result is None
    
    def test_validate_non_integer(self):
        """Test validation fails for non-integer input."""
        result = validate_conversation_number("abc", 10)
        assert result is None
        
        result = validate_conversation_number("5.5", 10)
        assert result is None


class TestProjectSelectionValidation:
    """Test project selection validation functionality."""
    
    def test_validate_valid_project_number(self):
        """Test validation of valid project number."""
        projects = [{"name": "proj1"}, {"name": "proj2"}, {"name": "proj3"}]
        result = validate_project_selection("2", projects)
        assert result == 1  # 0-based index
    
    def test_validate_project_number_too_low(self):
        """Test validation fails for project number too low."""
        projects = [{"name": "proj1"}]
        result = validate_project_selection("0", projects)
        assert result is None
    
    def test_validate_project_number_too_high(self):
        """Test validation fails for project number too high."""
        projects = [{"name": "proj1"}]
        result = validate_project_selection("5", projects)
        assert result is None
    
    def test_validate_file_path_selection(self):
        """Test validation of file path selection."""
        projects = [{"name": "proj1"}]
        result = validate_project_selection("/some/valid/path", projects)
        assert result == "/some/valid/path"
    
    def test_validate_empty_selection(self):
        """Test validation fails for empty selection."""
        projects = [{"name": "proj1"}]
        result = validate_project_selection("", projects)
        assert result is None
        
        result = validate_project_selection("   ", projects)
        assert result is None


class TestSearchTermSanitization:
    """Test search term sanitization functionality."""
    
    def test_sanitize_normal_text(self):
        """Test sanitization of normal text."""
        result = sanitize_search_term("hello world")
        assert result == "hello world"
    
    def test_sanitize_empty_string(self):
        """Test sanitization of empty string."""
        result = sanitize_search_term("")
        assert result == ""
    
    def test_sanitize_with_tabs_newlines(self):
        """Test sanitization preserves tabs and newlines."""
        result = sanitize_search_term("hello\tworld\ntest")
        assert result == "hello\tworld\ntest"
    
    def test_sanitize_remove_control_chars(self):
        """Test sanitization removes control characters."""
        # Control character (ASCII 7 - bell)
        result = sanitize_search_term("hello\x07world")
        assert result == "helloworld"
    
    def test_sanitize_length_limit(self):
        """Test sanitization respects length limit."""
        long_term = "a" * 200
        result = sanitize_search_term(long_term, max_length=50)
        assert len(result) == 50
        assert result == "a" * 50


class TestExportFormatValidation:
    """Test export format validation functionality."""
    
    def test_validate_valid_formats(self):
        """Test validation of valid export formats."""
        assert validate_export_format("text") == "text"
        assert validate_export_format("markdown") == "markdown"
        assert validate_export_format("json") == "json"
    
    def test_validate_case_insensitive(self):
        """Test validation is case insensitive."""
        assert validate_export_format("TEXT") == "text"
        assert validate_export_format("Markdown") == "markdown"
        assert validate_export_format("JSON") == "json"
    
    def test_validate_invalid_format(self):
        """Test validation fails for invalid format."""
        assert validate_export_format("xml") is None
        assert validate_export_format("pdf") is None
        assert validate_export_format("") is None


class TestCountParameterValidation:
    """Test count parameter validation functionality."""
    
    def test_validate_valid_count(self):
        """Test validation of valid count."""
        result = validate_count_parameter("10")
        assert result == 10
    
    def test_validate_count_at_bounds(self):
        """Test validation at boundary values."""
        result = validate_count_parameter("1", min_count=1, max_count=100)
        assert result == 1
        
        result = validate_count_parameter("100", min_count=1, max_count=100)
        assert result == 100
    
    def test_validate_count_below_minimum(self):
        """Test validation fails for count below minimum."""
        result = validate_count_parameter("0", min_count=1)
        assert result is None
    
    def test_validate_count_above_maximum(self):
        """Test validation fails for count above maximum."""
        result = validate_count_parameter("2000", max_count=1000)
        assert result is None
    
    def test_validate_non_integer_count(self):
        """Test validation fails for non-integer count."""
        result = validate_count_parameter("abc")
        assert result is None
        
        result = validate_count_parameter("10.5")
        assert result is None