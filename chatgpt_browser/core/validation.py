#!/usr/bin/env python3
"""Input validation utilities for ChatGPT Browser."""

import json
import os
from pathlib import Path
from typing import Optional, Union, Dict, Any

from chatgpt_browser.core.logging_config import get_logger

logger = get_logger(__name__)


def validate_file_path(file_path: str, must_exist: bool = True) -> Optional[Path]:
    """
    Validate and normalize a file path.
    
    Args:
        file_path: Path to validate
        must_exist: Whether the file must exist
        
    Returns:
        Normalized Path object if valid, None otherwise
    """
    try:
        path = Path(file_path).resolve()
        
        if must_exist and not path.exists():
            logger.warning(f"File does not exist: {path}")
            return None
            
        # Check if it's a valid path (not a directory when expecting file)
        
        
        return path
        
    except (OSError, ValueError) as e:
        logger.error(f"Invalid file path '{file_path}': {e}")
        return None


def validate_json_data(data: str, expect_array: bool = False) -> Optional[Union[Dict, list]]:
    """
    Validate and parse JSON data.
    
    Args:
        data: JSON string to validate
        expect_array: Whether to expect an array at root level
        
    Returns:
        Parsed JSON data if valid, None otherwise
    """
    try:
        parsed = json.loads(data)
        
        if expect_array and not isinstance(parsed, list):
            logger.warning("Expected JSON array but got different type")
            return None
            
        return parsed
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON data: {e}")
        return None


def validate_conversation_number(number: str, max_conversations: int) -> Optional[int]:
    """
    Validate conversation number input.
    
    Args:
        number: String representation of conversation number
        max_conversations: Maximum valid conversation number
        
    Returns:
        Validated conversation number (1-based) if valid, None otherwise
    """
    try:
        conv_num = int(number)
        
        if conv_num < 1:
            logger.warning(f"Conversation number must be positive: {conv_num}")
            return None
            
        if conv_num > max_conversations:
            logger.warning(f"Conversation number {conv_num} exceeds maximum {max_conversations}")
            return None
            
        return conv_num
        
    except ValueError:
        logger.warning(f"Invalid conversation number: '{number}' is not a valid integer")
        return None


def validate_project_selection(choice: str, available_projects: list) -> Optional[Union[int, str]]:
    """
    Validate project selection input.
    
    Args:
        choice: User input (project number or file path)
        available_projects: List of available projects
        
    Returns:
        Project index (0-based) if number, or validated path if string, None if invalid
    """
    choice = choice.strip()
    
    if not choice:
        logger.warning("Empty project selection")
        return None
    
    # Try to parse as project number
    try:
        project_num = int(choice)
        
        if project_num < 1:
            logger.warning(f"Project number must be positive: {project_num}")
            return None
            
        if project_num > len(available_projects):
            logger.warning(f"Project number {project_num} exceeds available projects ({len(available_projects)})")
            return None
            
        return project_num - 1  # Convert to 0-based index
        
    except ValueError:
        # Not a number, treat as file path
        validated_path = validate_file_path(choice, must_exist=False)
        if validated_path:
            return str(validated_path)
        else:
            logger.warning(f"Invalid project selection: '{choice}'")
            return None


def sanitize_search_term(term: str, max_length: int = 100) -> str:
    """
    Sanitize search term input.
    
    Args:
        term: Search term to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized search term
    """
    if not term:
        return ""
    
    # Remove control characters and limit length
    sanitized = ''.join(char for char in term if ord(char) >= 32 or char in '\t\n')
    sanitized = sanitized[:max_length]
    
    if len(sanitized) != len(term):
        logger.debug(f"Search term sanitized from '{term}' to '{sanitized}'")
    
    return sanitized


def validate_export_format(format_str: str) -> Optional[str]:
    """
    Validate export format string.
    
    Args:
        format_str: Format string to validate
        
    Returns:
        Validated format string if valid, None otherwise
    """
    valid_formats = {"text", "markdown", "json"}
    
    if format_str.lower() not in valid_formats:
        logger.warning(f"Invalid export format '{format_str}'. Valid formats: {valid_formats}")
        return None
    
    return format_str.lower()


def validate_count_parameter(count_str: str, min_count: int = 1, max_count: int = 1000) -> Optional[int]:
    """
    Validate count parameter for listings.
    
    Args:
        count_str: String representation of count
        min_count: Minimum allowed count
        max_count: Maximum allowed count
        
    Returns:
        Validated count if valid, None otherwise
    """
    try:
        count = int(count_str)
        
        if count < min_count:
            logger.warning(f"Count {count} is below minimum {min_count}")
            return None
            
        if count > max_count:
            logger.warning(f"Count {count} exceeds maximum {max_count}")
            return None
            
        return count
        
    except ValueError:
        logger.warning(f"Invalid count parameter: '{count_str}' is not a valid integer")
        return None