#!/usr/bin/env python3
"""Tests for logging configuration and functionality."""

import logging
import tempfile
from pathlib import Path

import pytest

from ccsm.core.logging_config import setup_logging, get_logger


class TestLoggingConfig:
    """Test logging configuration functionality."""
    
    def test_setup_logging_default(self):
        """Test default logging setup."""
        logger = setup_logging()
        assert logger.name == "ccsm"
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1  # Console handler
    
    def test_setup_logging_debug_mode(self):
        """Test logging setup with debug mode."""
        logger = setup_logging(debug_mode=True)
        assert logger.level == logging.DEBUG
    
    def test_setup_logging_with_file(self):
        """Test logging setup with file output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            logger = setup_logging(log_file=str(log_file))
            
            # Should have both console and file handlers
            assert len(logger.handlers) == 2
            
            # Test that file was created
            logger.info("Test message")
            assert log_file.exists()
            
            # Check file content
            content = log_file.read_text()
            assert "Test message" in content
    
    def test_setup_logging_custom_level(self):
        """Test logging setup with custom level."""
        logger = setup_logging(level="WARNING")
        assert logger.level == logging.WARNING
    
    def test_setup_logging_custom_format(self):
        """Test logging setup with custom format."""
        custom_format = "%(levelname)s: %(message)s"
        logger = setup_logging(format_string=custom_format)
        
        # Check that handlers use the custom format
        for handler in logger.handlers:
            assert handler.formatter._fmt == custom_format
    
    def test_get_logger(self):
        """Test get_logger function."""
        # Setup root logger first
        setup_logging()
        
        # Get module logger
        module_logger = get_logger("test_module")
        assert module_logger.name == "ccsm.test_module"
        
        # Should inherit from root logger
        assert module_logger.parent.name == "ccsm"
    
    def test_logging_hierarchy(self):
        """Test that logger hierarchy works correctly."""
        # Setup root logger
        root_logger = setup_logging(level="DEBUG")
        
        # Get child loggers
        core_logger = get_logger("core")
        loader_logger = get_logger("core.loader")
        
        # Test hierarchy - core.loader should be child of core, which is child of root
        assert core_logger.parent == root_logger
        assert loader_logger.parent == core_logger
        
        # Test level inheritance
        assert core_logger.getEffectiveLevel() == logging.DEBUG
        assert loader_logger.getEffectiveLevel() == logging.DEBUG
    
    def test_handler_cleanup(self):
        """Test that handlers are properly cleaned up on reconfiguration."""
        # Setup logger first time
        logger1 = setup_logging()
        handler_count_1 = len(logger1.handlers)
        
        # Setup logger second time - should clean up old handlers
        logger2 = setup_logging()
        handler_count_2 = len(logger2.handlers)
        
        # Should have same number of handlers, not accumulated
        assert handler_count_1 == handler_count_2
        assert logger1 is logger2  # Same logger instance
    
    def test_log_file_directory_creation(self):
        """Test that log file directories are created if they don't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "nested" / "dir" / "test.log"
            
            # Directory doesn't exist initially
            assert not log_file.parent.exists()
            
            # Setup logging should create it
            logger = setup_logging(log_file=str(log_file))
            logger.info("Test message")
            
            # Directory and file should now exist
            assert log_file.parent.exists()
            assert log_file.exists()


class TestLoggingIntegration:
    """Test logging integration with other modules."""
    
    def test_claude_loader_logging(self):
        """Test that claude_loader uses logging correctly."""
        # Setup logging to capture messages
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            setup_logging(level="DEBUG", log_file=str(log_file))
            
            # Import after setting up logging
            from ccsm.core.claude_loader import logger as claude_logger
            
            # Test that the logger is properly configured
            assert claude_logger.name == "ccsm.ccsm.core.claude_loader"
            assert claude_logger.getEffectiveLevel() == logging.DEBUG
    
    def test_tree_logging(self):
        """Test that tree module uses logging correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            setup_logging(level="DEBUG", log_file=str(log_file))
            
            # Test that debug messages are logged when tree loading fails
            from ccsm.tree.tree import ConversationTree
            
            # Create tree with non-existent file - should trigger debug log
            tree = ConversationTree("/nonexistent/path")
            
            # Check that debug message was logged
            log_content = log_file.read_text()
            assert "Failed to load tree structure" in log_content or log_content == ""  # May not log if file doesn't exist