#!/usr/bin/env python3
"""Context manager for proper curses initialization and cleanup."""

import curses
import logging
from contextlib import contextmanager
from typing import Generator, Any

from src.core.logging_config import get_logger

logger = get_logger(__name__)


@contextmanager
def curses_context() -> Generator[Any, None, None]:
    """
    Context manager for proper curses initialization and cleanup.
    
    Ensures that curses is properly cleaned up even if an exception occurs.
    
    Yields:
        The curses screen object
    """
    stdscr = None
    try:
        # Initialize curses
        stdscr = curses.initscr()
        
        # Configure curses settings
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)  # Hide cursor
        
        # Enable colors if available
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
        
        # Enable special keys
        stdscr.keypad(True)
        
        logger.debug("Curses initialized successfully")
        yield stdscr
        
    except Exception as e:
        logger.error(f"Error in curses context: {e}")
        raise
    finally:
        # Cleanup curses state
        try:
            if stdscr:
                stdscr.keypad(False)
                curses.curs_set(1)  # Restore cursor
                curses.nocbreak()
                curses.echo()
                curses.endwin()
                logger.debug("Curses cleaned up successfully")
        except curses.error as e:
            logger.warning(f"Error during curses cleanup: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during curses cleanup: {e}")


def emergency_cleanup():
    """
    Emergency curses cleanup function.
    
    Call this if the normal context manager cleanup fails.
    """
    try:
        curses.endwin()
        logger.info("Emergency curses cleanup completed")
    except Exception as e:
        logger.error(f"Emergency cleanup failed: {e}")