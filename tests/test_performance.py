#!/usr/bin/env python3
"""Tests for performance monitoring functionality."""

import time
import tempfile
from unittest.mock import Mock, patch, MagicMock
import pytest

from chatgpt_browser.core.performance import (
    PerformanceMetric,
    PerformanceMonitor,
    enable_performance_monitoring,
    get_performance_monitor,
    performance_timer,
    time_operation,
    memory_monitor,
    ProgressIndicator,
    profile_memory_usage,
    get_performance_summary
)


class TestPerformanceMetric:
    """Test PerformanceMetric functionality."""
    
    def test_metric_creation(self):
        """Test creating a performance metric."""
        start_time = time.time()
        metric = PerformanceMetric(
            name="test_operation",
            start_time=start_time,
            metadata={"test_key": "test_value"}
        )
        
        assert metric.name == "test_operation"
        assert metric.start_time == start_time
        assert metric.end_time is None
        assert metric.duration is None
        assert metric.metadata["test_key"] == "test_value"
    
    def test_finish_metric(self):
        """Test finishing a metric calculation."""
        start_time = time.time()
        metric = PerformanceMetric("test_operation", start_time)
        
        # Wait a small amount
        time.sleep(0.01)
        
        duration = metric.finish()
        
        assert metric.end_time is not None
        assert metric.duration is not None
        assert metric.duration > 0
        assert duration == metric.duration
        assert metric.duration >= 0.01
    
    def test_finish_metric_with_custom_end_time(self):
        """Test finishing metric with custom end time."""
        start_time = 1000.0
        end_time = 1001.5
        metric = PerformanceMetric("test_operation", start_time)
        
        duration = metric.finish(end_time)
        
        assert metric.end_time == end_time
        assert metric.duration == 1.5
        assert duration == 1.5
    
    def test_add_memory_usage(self):
        """Test adding memory usage information."""
        metric = PerformanceMetric("test_operation", time.time())
        
        metric.add_memory_usage(100.0, 150.0)
        
        assert metric.memory_before == 100.0
        assert metric.memory_after == 150.0
        assert metric.metadata["memory_delta"] == 50.0


class TestPerformanceMonitor:
    """Test PerformanceMonitor functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.monitor = PerformanceMonitor(enabled=True)
    
    def test_monitor_creation(self):
        """Test creating a performance monitor."""
        assert self.monitor.enabled is True
        assert len(self.monitor.metrics) == 0
        assert len(self.monitor.active_metrics) == 0
        assert len(self.monitor.aggregated_stats) == 0
    
    def test_measure_context_manager(self):
        """Test the measure context manager."""
        operation_name = "test_measure"
        
        with self.monitor.measure(operation_name, test_param="value") as metric:
            time.sleep(0.01)  # Simulate work
            assert isinstance(metric, PerformanceMetric)
            assert metric.name == operation_name
        
        # Check metric was recorded
        assert len(self.monitor.metrics) == 1
        recorded_metric = self.monitor.metrics[0]
        assert recorded_metric.name == operation_name
        assert recorded_metric.duration > 0
        assert recorded_metric.metadata["test_param"] == "value"
        
        # Check aggregated stats
        assert operation_name in self.monitor.aggregated_stats
        assert len(self.monitor.aggregated_stats[operation_name]) == 1
    
    def test_measure_disabled_monitor(self):
        """Test measure with disabled monitor."""
        disabled_monitor = PerformanceMonitor(enabled=False)
        
        with disabled_monitor.measure("test_operation") as metric:
            time.sleep(0.01)
        
        # Should not record anything
        assert len(disabled_monitor.metrics) == 0
        assert len(disabled_monitor.aggregated_stats) == 0
    
    def test_start_and_end_metric(self):
        """Test manual start and end metric."""
        operation_name = "manual_test"
        
        # Start metric
        metric = self.monitor.start_metric(operation_name, test_key="test_value")
        assert isinstance(metric, PerformanceMetric)
        assert metric.name == operation_name
        assert operation_name in self.monitor.active_metrics
        
        # Simulate work
        time.sleep(0.01)
        
        # End metric
        duration = self.monitor.end_metric(operation_name)
        assert duration > 0
        assert operation_name not in self.monitor.active_metrics
        assert len(self.monitor.metrics) == 1
        
        recorded_metric = self.monitor.metrics[0]
        assert recorded_metric.name == operation_name
        assert recorded_metric.duration == duration
        assert recorded_metric.metadata["test_key"] == "test_value"
    
    def test_end_nonexistent_metric(self):
        """Test ending a metric that doesn't exist."""
        duration = self.monitor.end_metric("nonexistent")
        assert duration is None
    
    @patch('chatgpt_browser.core.performance.psutil.Process')
    def test_memory_tracking(self, mock_process):
        """Test memory usage tracking."""
        # Mock memory info
        mock_memory_info = Mock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100MB in bytes
        mock_process.return_value.memory_info.return_value = mock_memory_info
        
        with self.monitor.measure("memory_test"):
            pass
        
        metric = self.monitor.metrics[0]
        assert metric.memory_before is not None
        assert metric.memory_after is not None
        assert metric.metadata.get("memory_delta") is not None
    
    def test_get_stats(self):
        """Test getting performance statistics."""
        # Record multiple metrics
        with self.monitor.measure("operation_a"):
            time.sleep(0.01)
        
        with self.monitor.measure("operation_a"):
            time.sleep(0.005)
        
        with self.monitor.measure("operation_b"):
            time.sleep(0.02)
        
        stats = self.monitor.get_stats()
        
        # Check operation_a stats
        assert "operation_a" in stats
        op_a_stats = stats["operation_a"]
        assert op_a_stats["count"] == 2
        assert op_a_stats["total_time"] > 0
        assert op_a_stats["avg_time"] > 0
        assert op_a_stats["min_time"] > 0
        assert op_a_stats["max_time"] > 0
        
        # Check operation_b stats
        assert "operation_b" in stats
        op_b_stats = stats["operation_b"]
        assert op_b_stats["count"] == 1
        
        # Check system stats
        assert "system" in stats
        assert isinstance(stats["system"], dict)
    
    def test_get_recent_metrics(self):
        """Test getting recent metrics."""
        # Record several metrics
        for i in range(5):
            with self.monitor.measure(f"operation_{i}"):
                pass
        
        # Get recent metrics
        recent = self.monitor.get_recent_metrics(3)
        assert len(recent) == 3
        assert all(isinstance(m, PerformanceMetric) for m in recent)
        
        # Should be the last 3
        assert recent[0].name == "operation_2"
        assert recent[1].name == "operation_3" 
        assert recent[2].name == "operation_4"
    
    def test_clear_metrics(self):
        """Test clearing all metrics."""
        # Record some metrics
        with self.monitor.measure("test_operation"):
            pass
        
        assert len(self.monitor.metrics) == 1
        assert len(self.monitor.aggregated_stats) == 1
        
        self.monitor.clear_metrics()
        
        assert len(self.monitor.metrics) == 0
        assert len(self.monitor.aggregated_stats) == 0
        assert len(self.monitor.active_metrics) == 0
    
    def test_log_slow_operations(self):
        """Test logging slow operations."""
        # Create metrics with different durations
        fast_metric = PerformanceMetric("fast_op", time.time())
        fast_metric.finish(fast_metric.start_time + 0.1)
        
        slow_metric = PerformanceMetric("slow_op", time.time())  
        slow_metric.finish(slow_metric.start_time + 2.0)
        
        self.monitor.metrics = [fast_metric, slow_metric]
        
        with patch.object(self.monitor.logger, 'warning') as mock_warning:
            self.monitor.log_slow_operations(threshold_seconds=1.0)
            
            # Should log warning about slow operation
            assert mock_warning.call_count == 2  # One for summary, one for slow op
            warning_calls = [call[0][0] for call in mock_warning.call_args_list]
            assert any("slow operations" in call for call in warning_calls)
            assert any("slow_op: 2.000s" in call for call in warning_calls)


class TestGlobalPerformanceMonitor:
    """Test global performance monitor functions."""
    
    def test_enable_disable_monitoring(self):
        """Test enabling and disabling performance monitoring."""
        # Test enable
        enable_performance_monitoring(True)
        monitor = get_performance_monitor()
        assert monitor.enabled is True
        
        # Test disable
        enable_performance_monitoring(False)
        assert monitor.enabled is False
    
    def test_get_performance_monitor(self):
        """Test getting global monitor instance."""
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()
        
        # Should be same instance
        assert monitor1 is monitor2
    
    def test_performance_timer_decorator(self):
        """Test performance timer decorator."""
        enable_performance_monitoring(True)
        monitor = get_performance_monitor()
        monitor.clear_metrics()
        
        @performance_timer("test_function")
        def test_function():
            time.sleep(0.01)
            return "result"
        
        result = test_function()
        
        assert result == "result"
        assert len(monitor.metrics) == 1
        assert monitor.metrics[0].name == "test_function"
        assert monitor.metrics[0].duration > 0
    
    def test_performance_timer_default_name(self):
        """Test performance timer with default name."""
        enable_performance_monitoring(True)
        monitor = get_performance_monitor()
        monitor.clear_metrics()
        
        @performance_timer()
        def another_test_function():
            return "result"
        
        another_test_function()
        
        assert len(monitor.metrics) == 1
        # Should use module.function format
        assert "another_test_function" in monitor.metrics[0].name
    
    def test_time_operation_context_manager(self):
        """Test time_operation context manager."""
        enable_performance_monitoring(True)
        monitor = get_performance_monitor()
        monitor.clear_metrics()
        
        with time_operation("context_test"):
            time.sleep(0.01)
        
        assert len(monitor.metrics) == 1
        assert monitor.metrics[0].name == "context_test"
        assert monitor.metrics[0].duration > 0
    
    @patch('chatgpt_browser.core.performance.psutil.Process')
    def test_memory_monitor_context_manager(self, mock_process):
        """Test memory monitor context manager."""
        enable_performance_monitoring(True)
        
        # Mock memory usage progression
        mock_memory_info = Mock()
        mock_process.return_value.memory_info.return_value = mock_memory_info
        mock_memory_info.rss = 100 * 1024 * 1024  # 100MB
        
        with patch('chatgpt_browser.core.performance.logger') as mock_logger:
            with memory_monitor("memory_test"):
                # Simulate memory increase
                mock_memory_info.rss = 102 * 1024 * 1024  # 102MB
                time.sleep(0.01)
        
        # Should have logged memory usage (delta > 1MB)
        mock_logger.debug.assert_called()
        log_message = mock_logger.debug.call_args[0][0]
        assert "memory_test used" in log_message
    
    def test_memory_monitor_disabled(self):
        """Test memory monitor when disabled."""
        enable_performance_monitoring(False)
        
        with memory_monitor("disabled_test"):
            time.sleep(0.01)
        
        # Should complete without issues, no logging
    
    def test_profile_memory_usage_decorator(self):
        """Test profile memory usage decorator."""
        enable_performance_monitoring(True)
        
        with patch('chatgpt_browser.core.performance.logger') as mock_logger:
            @profile_memory_usage
            def memory_function():
                return "result"
            
            result = memory_function()
            
            assert result == "result"
            # Function name should be in logger call if memory usage is significant


class TestProgressIndicator:
    """Test ProgressIndicator functionality."""
    
    def test_progress_creation(self):
        """Test creating progress indicator."""
        progress = ProgressIndicator(100, "Testing progress")
        
        assert progress.total_items == 100
        assert progress.current_item == 0
        assert progress.description == "Testing progress"
        assert progress.start_time > 0
    
    def test_progress_update(self):
        """Test updating progress."""
        progress = ProgressIndicator(10, "Test progress")
        
        with patch.object(progress.logger, 'info') as mock_info:
            # Update progress
            progress.update(3)
            assert progress.current_item == 3
            
            # Should log progress
            mock_info.assert_called()
            log_message = mock_info.call_args[0][0]
            assert "Test progress: 3/10" in log_message
            assert "30.0%" in log_message
    
    def test_progress_update_with_timing(self):
        """Test progress update with ETA calculation."""
        progress = ProgressIndicator(100, "Timed progress")
        
        # Simulate some time passing
        with patch('time.time') as mock_time:
            mock_time.side_effect = [1000.0, 1000.0, 1002.0]  # 2 seconds elapsed
            
            progress = ProgressIndicator(100, "Timed progress") 
            
            with patch.object(progress.logger, 'info') as mock_info:
                progress.update(20)  # 20% complete in 2 seconds
                
                mock_info.assert_called()
                log_message = mock_info.call_args[0][0]
                assert "ETA:" in log_message
    
    def test_progress_finish(self):
        """Test finishing progress."""
        progress = ProgressIndicator(50, "Finish test")
        
        # Update partway
        progress.update(25)
        
        with patch.object(progress.logger, 'info') as mock_info:
            progress.finish()
            
            assert progress.current_item == 50
            mock_info.assert_called()
            log_message = mock_info.call_args[0][0]
            assert "Finish test completed: 50 items" in log_message
            assert "items/sec" in log_message
    
    def test_progress_zero_items(self):
        """Test progress with zero total items."""
        progress = ProgressIndicator(0, "Empty progress")
        
        with patch.object(progress.logger, 'info') as mock_info:
            progress.update()
            # Should not crash and not log (since total is 0)
            assert mock_info.call_count == 0


class TestPerformanceIntegration:
    """Integration tests for performance monitoring."""
    
    def test_get_performance_summary(self):
        """Test getting comprehensive performance summary."""
        enable_performance_monitoring(True)
        monitor = get_performance_monitor()
        monitor.clear_metrics()
        
        # Record some operations
        with time_operation("fast_operation"):
            time.sleep(0.01)
        
        with time_operation("slow_operation"):
            time.sleep(0.6)  # > 0.5s threshold
        
        summary = get_performance_summary()
        
        assert "fast_operation" in summary
        assert "slow_operation" in summary
        assert "slow_operations" in summary
        assert "total_metrics" in summary
        assert "system" in summary
        
        # Should identify slow operation
        slow_ops = summary["slow_operations"]
        assert len(slow_ops) == 1
        assert slow_ops[0]["name"] == "slow_operation"
        assert slow_ops[0]["duration"] > 0.5
    
    def test_nested_performance_monitoring(self):
        """Test nested performance monitoring."""
        enable_performance_monitoring(True)
        monitor = get_performance_monitor()
        monitor.clear_metrics()
        
        with time_operation("outer_operation"):
            time.sleep(0.01)
            
            with time_operation("inner_operation"):
                time.sleep(0.01)
            
            time.sleep(0.01)
        
        assert len(monitor.metrics) == 2
        
        # Find operations
        outer = next(m for m in monitor.metrics if m.name == "outer_operation")
        inner = next(m for m in monitor.metrics if m.name == "inner_operation")
        
        # Outer should take longer than inner
        assert outer.duration > inner.duration
        assert outer.duration >= 0.03  # Approximately 3 sleep calls
        assert inner.duration >= 0.01  # Approximately 1 sleep call
    
    def test_performance_monitoring_with_exceptions(self):
        """Test that performance monitoring handles exceptions correctly."""
        enable_performance_monitoring(True)
        monitor = get_performance_monitor()
        monitor.clear_metrics()
        
        try:
            with time_operation("exception_test"):
                time.sleep(0.01)
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Should still record the metric
        assert len(monitor.metrics) == 1
        assert monitor.metrics[0].name == "exception_test"
        assert monitor.metrics[0].duration > 0
    
    @patch('chatgpt_browser.core.performance.psutil.Process')
    def test_system_stats_collection(self, mock_process):
        """Test system statistics collection."""
        # Mock psutil data
        mock_process.return_value.memory_info.return_value.rss = 100 * 1024 * 1024
        
        with patch('chatgpt_browser.core.performance.psutil.cpu_percent', return_value=25.5):
            with patch('chatgpt_browser.core.performance.psutil.virtual_memory') as mock_vmem:
                mock_vmem.return_value.percent = 60.0
                
                with patch('chatgpt_browser.core.performance.psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 80.0
                    
                    monitor = PerformanceMonitor()
                    stats = monitor._get_system_stats()
                    
                    assert stats['memory_usage_mb'] == 100.0
                    assert stats['cpu_percent'] == 25.5
                    assert stats['memory_percent'] == 60.0
                    assert stats['disk_usage_percent'] == 80.0