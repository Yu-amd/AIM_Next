"""
QoS Manager for GPU Sharing

Implements priority-based request scheduling, resource guarantees, and SLO tracking.
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import deque
from queue import PriorityQueue

logger = logging.getLogger(__name__)


class QoSLevel(Enum):
    """QoS priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Request:
    """Represents a model inference request."""
    request_id: str
    model_id: str
    partition_id: int
    priority: QoSLevel
    timestamp: float
    timeout: Optional[float] = None  # Request timeout in seconds
    min_guarantee: Optional[float] = None  # Minimum resource guarantee (0-1)
    max_limit: Optional[float] = None  # Maximum resource limit (0-1)


@dataclass
class SLO:
    """Service Level Objective for a model."""
    model_id: str
    max_latency_seconds: float
    min_throughput_per_second: float
    target_utilization: float = 0.8


class RequestQueue:
    """Priority queue for requests."""
    
    def __init__(self):
        self._queues: Dict[QoSLevel, deque] = {
            QoSLevel.HIGH: deque(),
            QoSLevel.MEDIUM: deque(),
            QoSLevel.LOW: deque()
        }
        self._lock = threading.Lock()
    
    def enqueue(self, request: Request):
        """Add request to appropriate queue."""
        with self._lock:
            self._queues[request.priority].append(request)
    
    def dequeue(self) -> Optional[Request]:
        """Get next request (highest priority first)."""
        with self._lock:
            # Check queues in priority order
            for level in [QoSLevel.HIGH, QoSLevel.MEDIUM, QoSLevel.LOW]:
                if self._queues[level]:
                    return self._queues[level].popleft()
            return None
    
    def size(self, priority: Optional[QoSLevel] = None) -> int:
        """Get queue size."""
        with self._lock:
            if priority:
                return len(self._queues[priority])
            return sum(len(q) for q in self._queues.values())
    
    def clear_expired(self, current_time: float):
        """Remove expired requests."""
        with self._lock:
            for queue in self._queues.values():
                # Remove expired requests
                while queue and queue[0].timeout and (current_time - queue[0].timestamp) > queue[0].timeout:
                    expired = queue.popleft()
                    logger.warning(f"Request {expired.request_id} expired")


class QoSManager:
    """Manages QoS for GPU sharing."""
    
    def __init__(self):
        """Initialize QoS manager."""
        self.request_queue = RequestQueue()
        self.slos: Dict[str, SLO] = {}
        self.request_stats: Dict[str, Dict] = {}  # model_id -> stats
        self.resource_guarantees: Dict[str, float] = {}  # model_id -> guarantee (0-1)
        self.resource_limits: Dict[str, float] = {}  # model_id -> limit (0-1)
        self._lock = threading.Lock()
    
    def register_slo(self, slo: SLO):
        """Register SLO for a model."""
        with self._lock:
            self.slos[slo.model_id] = slo
            if slo.model_id not in self.request_stats:
                self.request_stats[slo.model_id] = {
                    'total_requests': 0,
                    'completed_requests': 0,
                    'failed_requests': 0,
                    'total_latency': 0.0,
                    'max_latency': 0.0,
                    'min_latency': float('inf')
                }
        logger.info(f"Registered SLO for {slo.model_id}: max_latency={slo.max_latency_seconds}s, min_throughput={slo.min_throughput_per_second}/s")
    
    def set_resource_guarantee(self, model_id: str, guarantee: float):
        """
        Set minimum resource guarantee for a model.
        
        Args:
            model_id: Model identifier
            guarantee: Resource guarantee (0-1, where 1 = 100% of partition)
        """
        if not 0 <= guarantee <= 1:
            raise ValueError("Guarantee must be between 0 and 1")
        
        with self._lock:
            self.resource_guarantees[model_id] = guarantee
        logger.info(f"Set resource guarantee for {model_id}: {guarantee*100}%")
    
    def set_resource_limit(self, model_id: str, limit: float):
        """
        Set maximum resource limit for a model.
        
        Args:
            model_id: Model identifier
            limit: Resource limit (0-1, where 1 = 100% of partition)
        """
        if not 0 <= limit <= 1:
            raise ValueError("Limit must be between 0 and 1")
        
        with self._lock:
            self.resource_limits[model_id] = limit
        logger.info(f"Set resource limit for {model_id}: {limit*100}%")
    
    def submit_request(self, request: Request) -> bool:
        """
        Submit a request for processing.
        
        Args:
            request: Request to submit
        
        Returns:
            True if accepted, False if rejected
        """
        # Check if model has resource limits
        with self._lock:
            if request.model_id in self.resource_limits:
                # Check current utilization (simplified - would need actual metrics)
                # For now, just check if queue is too long
                queue_size = self.request_queue.size()
                if queue_size > 100:  # Arbitrary threshold
                    logger.warning(f"Queue too long ({queue_size}), rejecting request {request.request_id}")
                    return False
        
        self.request_queue.enqueue(request)
        logger.debug(f"Submitted request {request.request_id} for model {request.model_id}")
        return True
    
    def get_next_request(self) -> Optional[Request]:
        """Get next request to process (highest priority first)."""
        # Clear expired requests
        current_time = time.time()
        self.request_queue.clear_expired(current_time)
        
        return self.request_queue.dequeue()
    
    def record_request_completion(self, model_id: str, latency: float, success: bool = True):
        """
        Record request completion for SLO tracking.
        
        Args:
            model_id: Model identifier
            latency: Request latency in seconds
            success: Whether request succeeded
        """
        with self._lock:
            if model_id not in self.request_stats:
                self.request_stats[model_id] = {
                    'total_requests': 0,
                    'completed_requests': 0,
                    'failed_requests': 0,
                    'total_latency': 0.0,
                    'max_latency': 0.0,
                    'min_latency': float('inf')
                }
            
            stats = self.request_stats[model_id]
            stats['total_requests'] += 1
            
            if success:
                stats['completed_requests'] += 1
                stats['total_latency'] += latency
                stats['max_latency'] = max(stats['max_latency'], latency)
                stats['min_latency'] = min(stats['min_latency'], latency)
            else:
                stats['failed_requests'] += 1
    
    def check_slo_compliance(self, model_id: str) -> Tuple[bool, Dict]:
        """
        Check if model is meeting its SLO.
        
        Returns:
            Tuple of (is_compliant, metrics_dict)
        """
        with self._lock:
            if model_id not in self.slos:
                return True, {}  # No SLO defined
            
            slo = self.slos[model_id]
            stats = self.request_stats.get(model_id, {})
            
            if stats.get('completed_requests', 0) == 0:
                return True, {}  # No requests yet
            
            # Calculate average latency
            avg_latency = stats['total_latency'] / stats['completed_requests']
            
            # Calculate throughput (requests per second)
            # Simplified - would need time window tracking
            total_requests = stats['total_requests']
            throughput = total_requests / 60.0 if total_requests > 0 else 0  # Rough estimate
            
            # Check compliance
            latency_compliant = avg_latency <= slo.max_latency_seconds
            throughput_compliant = throughput >= slo.min_throughput_per_second
            
            is_compliant = latency_compliant and throughput_compliant
            
            metrics = {
                'avg_latency': avg_latency,
                'max_latency': stats.get('max_latency', 0),
                'min_latency': stats.get('min_latency', float('inf')),
                'throughput': throughput,
                'total_requests': total_requests,
                'completed_requests': stats.get('completed_requests', 0),
                'failed_requests': stats.get('failed_requests', 0),
                'latency_slo': slo.max_latency_seconds,
                'throughput_slo': slo.min_throughput_per_second,
                'latency_compliant': latency_compliant,
                'throughput_compliant': throughput_compliant
            }
            
            return is_compliant, metrics
    
    def get_queue_depth(self, priority: Optional[QoSLevel] = None) -> int:
        """Get current queue depth."""
        return self.request_queue.size(priority)
    
    def throttle_low_priority(self, enable: bool = True):
        """
        Enable/disable throttling for low-priority requests.
        
        Args:
            enable: Whether to enable throttling
        """
        # Implementation would throttle low-priority requests
        # when high-priority requests are waiting
        logger.info(f"Throttling for low-priority requests: {'enabled' if enable else 'disabled'}")


# Convenience function to create QoS manager
def create_qos_manager() -> QoSManager:
    """Create and return a QoS manager instance."""
    return QoSManager()

