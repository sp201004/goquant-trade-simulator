"""
Performance monitoring utilities for latency measurement.
"""

import time
import psutil
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import deque
import statistics


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    processing_latency_ms: float = 0.0
    ui_update_latency_ms: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    network_latency_ms: float = 0.0
    ticks_per_second: float = 0.0
    

class LatencyTracker:
    """Track and calculate latency metrics."""
    
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self.samples: deque = deque(maxlen=max_samples)
        self.start_times: Dict[str, float] = {}
        
    def start_timer(self, operation_id: str) -> None:
        """Start timing an operation."""
        self.start_times[operation_id] = time.perf_counter()
        
    def end_timer(self, operation_id: str) -> Optional[float]:
        """End timing an operation and return latency in milliseconds."""
        if operation_id not in self.start_times:
            return None
            
        start_time = self.start_times.pop(operation_id)
        latency_ms = (time.perf_counter() - start_time) * 1000
        self.samples.append(latency_ms)
        return latency_ms
        
    def get_statistics(self) -> Dict[str, float]:
        """Get latency statistics."""
        if not self.samples:
            return {"mean": 0.0, "median": 0.0, "p95": 0.0, "p99": 0.0, "min": 0.0, "max": 0.0}
            
        samples_list = list(self.samples)
        return {
            "mean": statistics.mean(samples_list),
            "median": statistics.median(samples_list),
            "p95": self._percentile(samples_list, 95),
            "p99": self._percentile(samples_list, 99),
            "min": min(samples_list),
            "max": max(samples_list)
        }
        
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int((percentile / 100.0) * len(sorted_data))
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        return sorted_data[index]


class PerformanceMonitor:
    """Monitor system and application performance."""
    
    def __init__(self):
        self.processing_tracker = LatencyTracker()
        self.ui_tracker = LatencyTracker()
        self.network_tracker = LatencyTracker()
        self.tick_counter = 0
        self.last_tick_time = time.time()
        self.process = psutil.Process()
        
    def start_processing_timer(self, tick_id: str) -> None:
        """Start timing data processing."""
        self.processing_tracker.start_timer(tick_id)
        
    def end_processing_timer(self, tick_id: str) -> Optional[float]:
        """End timing data processing."""
        return self.processing_tracker.end_timer(tick_id)
        
    def start_ui_timer(self, update_id: str) -> None:
        """Start timing UI update."""
        self.ui_tracker.start_timer(update_id)
        
    def end_ui_timer(self, update_id: str) -> Optional[float]:
        """End timing UI update."""
        return self.ui_tracker.end_timer(update_id)
        
    def record_network_latency(self, latency_ms: float) -> None:
        """Record network latency measurement."""
        self.network_tracker.samples.append(latency_ms)
        
    def record_tick(self) -> None:
        """Record a data tick for TPS calculation."""
        self.tick_counter += 1
        
    def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        # Calculate ticks per second
        current_time = time.time()
        time_diff = current_time - self.last_tick_time
        if time_diff >= 1.0:  # Update every second
            tps = self.tick_counter / time_diff
            self.tick_counter = 0
            self.last_tick_time = current_time
        else:
            tps = 0.0
            
        # Get system metrics
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        cpu_percent = self.process.cpu_percent()
        
        # Get latency statistics
        processing_stats = self.processing_tracker.get_statistics()
        ui_stats = self.ui_tracker.get_statistics()
        network_stats = self.network_tracker.get_statistics()
        
        return PerformanceMetrics(
            processing_latency_ms=processing_stats["mean"],
            ui_update_latency_ms=ui_stats["mean"],
            memory_usage_mb=memory_mb,
            cpu_usage_percent=cpu_percent,
            network_latency_ms=network_stats["mean"],
            ticks_per_second=tps
        )
        
    def get_detailed_stats(self) -> Dict[str, Dict[str, float]]:
        """Get detailed latency statistics."""
        return {
            "processing": self.processing_tracker.get_statistics(),
            "ui_updates": self.ui_tracker.get_statistics(),
            "network": self.network_tracker.get_statistics()
        }


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
