#!/usr/bin/env python3
"""Performance monitoring and profiling utilities."""

import time
import psutil
import functools
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from contextlib import contextmanager

from chatgpt_browser.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetric:
    """Individual performance metric."""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    memory_before: Optional[float] = None
    memory_after: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self, end_time: Optional[float] = None) -> float:
        """Mark the metric as finished and calculate duration."""
        self.end_time = end_time or time.time()
        self.duration = self.end_time - self.start_time
        return self.duration
    
    def add_memory_usage(self, before: float, after: float) -> None:
        """Add memory usage information."""
        self.memory_before = before
        self.memory_after = after
        self.metadata['memory_delta'] = after - before


class PerformanceMonitor:
    """Performance monitoring and metrics collection."""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.metrics: List[PerformanceMetric] = []
        self.active_metrics: Dict[str, PerformanceMetric] = {}
        self.aggregated_stats: Dict[str, List[float]] = defaultdict(list)
        self.logger = get_logger(__name__)
    
    @contextmanager
    def measure(self, operation_name: str, **metadata):
        """Context manager for measuring operation performance."""
        if not self.enabled:
            yield
            return
        
        metric = self.start_metric(operation_name, **metadata)
        try:
            yield metric
        finally:
            self.end_metric(operation_name)
    
    def start_metric(self, name: str, **metadata) -> PerformanceMetric:
        """Start measuring a performance metric."""
        if not self.enabled:
            return PerformanceMetric(name, time.time())
        
        memory_before = self._get_memory_usage()
        metric = PerformanceMetric(
            name=name,
            start_time=time.time(),
            memory_before=memory_before,
            metadata=metadata
        )
        
        self.active_metrics[name] = metric
        return metric
    
    def end_metric(self, name: str) -> Optional[float]:
        """End measuring a performance metric."""
        if not self.enabled:
            return None
        
        metric = self.active_metrics.pop(name, None)
        if not metric:
            self.logger.warning(f"No active metric found for: {name}")
            return None
        
        duration = metric.finish()
        memory_after = self._get_memory_usage()
        if metric.memory_before is not None:
            metric.add_memory_usage(metric.memory_before, memory_after)
        
        self.metrics.append(metric)
        self.aggregated_stats[name].append(duration)
        
        self.logger.debug(f"Performance: {name} took {duration:.3f}s")
        return duration
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated performance statistics."""
        stats = {}
        
        for name, durations in self.aggregated_stats.items():
            if durations:
                stats[name] = {
                    'count': len(durations),
                    'total_time': sum(durations),
                    'avg_time': sum(durations) / len(durations),
                    'min_time': min(durations),
                    'max_time': max(durations),
                    'last_time': durations[-1] if durations else 0
                }
        
        # Add system stats
        stats['system'] = self._get_system_stats()
        return stats
    
    def get_recent_metrics(self, limit: int = 10) -> List[PerformanceMetric]:
        """Get the most recent performance metrics."""
        return self.metrics[-limit:] if self.metrics else []
    
    def clear_metrics(self) -> None:
        """Clear all stored metrics."""
        self.metrics.clear()
        self.aggregated_stats.clear()
        self.active_metrics.clear()
        self.logger.debug("Performance metrics cleared")
    
    def log_slow_operations(self, threshold_seconds: float = 1.0) -> None:
        """Log operations that took longer than the threshold."""
        slow_ops = [
            metric for metric in self.metrics
            if metric.duration and metric.duration > threshold_seconds
        ]
        
        if slow_ops:
            self.logger.warning(f"Found {len(slow_ops)} slow operations (>{threshold_seconds}s):")
            for metric in slow_ops:
                self.logger.warning(f"  {metric.name}: {metric.duration:.3f}s")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except (psutil.NoSuchProcess, AttributeError):
            return 0.0
    
    def _get_system_stats(self) -> Dict[str, Any]:
        """Get current system performance statistics."""
        try:
            return {
                'memory_usage_mb': self._get_memory_usage(),
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage_percent': psutil.disk_usage('/').percent
            }
        except (psutil.NoSuchProcess, AttributeError):
            return {}


# Global performance monitor instance
_performance_monitor = PerformanceMonitor(enabled=False)  # Disabled by default


def enable_performance_monitoring(enabled: bool = True) -> None:
    """Enable or disable global performance monitoring."""
    global _performance_monitor
    _performance_monitor.enabled = enabled
    logger.info(f"Performance monitoring {'enabled' if enabled else 'disabled'}")


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return _performance_monitor


def performance_timer(operation_name: Optional[str] = None):
    """Decorator for timing function execution."""
    def decorator(func: Callable) -> Callable:
        name = operation_name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with _performance_monitor.measure(name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def time_operation(name: str):
    """Context manager for timing operations."""
    return _performance_monitor.measure(name)


@contextmanager
def memory_monitor(operation_name: str):
    """Context manager for monitoring memory usage during an operation."""
    if not _performance_monitor.enabled:
        yield
        return
    
    memory_before = _performance_monitor._get_memory_usage()
    start_time = time.time()
    
    try:
        yield
    finally:
        memory_after = _performance_monitor._get_memory_usage()
        duration = time.time() - start_time
        memory_delta = memory_after - memory_before
        
        if memory_delta > 1.0:  # Log if memory increased by more than 1MB
            logger.debug(
                f"Memory usage: {operation_name} used {memory_delta:.1f}MB "
                f"(before: {memory_before:.1f}MB, after: {memory_after:.1f}MB) "
                f"in {duration:.3f}s"
            )


class ProgressIndicator:
    """Progress indicator for long-running operations."""
    
    def __init__(self, total_items: int, description: str = "Processing"):
        self.total_items = total_items
        self.current_item = 0
        self.description = description
        self.start_time = time.time()
        self.last_update = 0
        self.update_interval = 1.0  # Update every second
        self.logger = get_logger(__name__)
    
    def update(self, increment: int = 1) -> None:
        """Update progress by the specified increment."""
        self.current_item += increment
        current_time = time.time()
        
        # Only update if enough time has passed or we're done
        if (current_time - self.last_update >= self.update_interval or 
            self.current_item >= self.total_items):
            
            self._log_progress()
            self.last_update = current_time
    
    def finish(self) -> None:
        """Mark progress as finished."""
        self.current_item = self.total_items
        self._log_progress()
        
        total_time = time.time() - self.start_time
        rate = self.total_items / total_time if total_time > 0 else 0
        self.logger.info(
            f"{self.description} completed: {self.total_items} items "
            f"in {total_time:.1f}s ({rate:.1f} items/sec)"
        )
    
    def _log_progress(self) -> None:
        """Log current progress."""
        if self.total_items == 0:
            return
        
        percentage = (self.current_item / self.total_items) * 100
        elapsed = time.time() - self.start_time
        
        if elapsed > 0 and self.current_item > 0:
            rate = self.current_item / elapsed
            eta = (self.total_items - self.current_item) / rate if rate > 0 else 0
            
            self.logger.info(
                f"{self.description}: {self.current_item}/{self.total_items} "
                f"({percentage:.1f}%) - ETA: {eta:.1f}s"
            )


def profile_memory_usage(func: Callable) -> Callable:
    """Decorator to profile memory usage of a function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with memory_monitor(f"{func.__module__}.{func.__name__}"):
            return func(*args, **kwargs)
    return wrapper


def get_performance_summary() -> Dict[str, Any]:
    """Get a comprehensive performance summary."""
    monitor = get_performance_monitor()
    stats = monitor.get_stats()
    
    # Add recent slow operations
    recent_metrics = monitor.get_recent_metrics(20)
    slow_operations = [
        {
            'name': metric.name,
            'duration': metric.duration,
            'memory_delta': metric.metadata.get('memory_delta', 0)
        }
        for metric in recent_metrics
        if metric.duration and metric.duration > 0.5
    ]
    
    stats['slow_operations'] = slow_operations
    stats['total_metrics'] = len(monitor.metrics)
    
    return stats