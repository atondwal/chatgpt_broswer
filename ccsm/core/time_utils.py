#!/usr/bin/env python3
"""Time formatting utilities."""

from datetime import datetime, timedelta
from typing import Optional


def format_relative_time(timestamp: Optional[float]) -> str:
    """Format timestamp as relative time (e.g., '2h ago', '3 days ago')."""
    if not timestamp:
        return "Unknown"
    
    now = datetime.now()
    then = datetime.fromtimestamp(timestamp)
    delta = now - then
    
    # Less than an hour
    if delta < timedelta(hours=1):
        minutes = int(delta.total_seconds() / 60)
        if minutes < 1:
            return "Just now"
        elif minutes == 1:
            return "1m ago"
        else:
            return f"{minutes}m ago"
    
    # Less than a day
    elif delta < timedelta(days=1):
        hours = int(delta.total_seconds() / 3600)
        if hours == 1:
            return "1h ago"
        else:
            return f"{hours}h ago"
    
    # Less than a week
    elif delta < timedelta(days=7):
        days = delta.days
        if days == 1:
            return "1 day ago"
        else:
            return f"{days} days ago"
    
    # Less than a month
    elif delta < timedelta(days=30):
        weeks = delta.days // 7
        if weeks == 1:
            return "1 week ago"
        else:
            return f"{weeks} weeks ago"
    
    # Less than a year
    elif delta < timedelta(days=365):
        months = delta.days // 30
        if months == 1:
            return "1 month ago"
        else:
            return f"{months} months ago"
    
    # More than a year
    else:
        years = delta.days // 365
        if years == 1:
            return "1 year ago"
        else:
            return f"{years} years ago"