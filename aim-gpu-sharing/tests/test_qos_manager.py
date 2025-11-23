"""
Tests for QoS Manager
"""

import sys
import pytest
import time
from pathlib import Path

# Add runtime to path
runtime_path = Path(__file__).parent.parent / "runtime"
sys.path.insert(0, str(runtime_path))

# Add qos subdirectory
qos_path = runtime_path / "qos"
sys.path.insert(0, str(qos_path))

from qos.qos_manager import QoSManager, QoSLevel, Request, SLO


class TestQoSManager:
    """Test QoS Manager functionality."""
    
    def test_initialization(self):
        """Test QoS manager initialization."""
        manager = QoSManager()
        assert manager is not None
        assert manager.request_queue is not None
        assert len(manager.slos) == 0
    
    def test_register_slo(self):
        """Test SLO registration."""
        manager = QoSManager()
        slo = SLO(
            model_id="test-model",
            max_latency_seconds=1.0,
            min_throughput_per_second=10.0
        )
        manager.register_slo(slo)
        assert "test-model" in manager.slos
        assert manager.slos["test-model"] == slo
    
    def test_set_resource_guarantee(self):
        """Test setting resource guarantee."""
        manager = QoSManager()
        manager.set_resource_guarantee("test-model", 0.5)
        assert manager.resource_guarantees["test-model"] == 0.5
    
    def test_set_resource_guarantee_invalid(self):
        """Test invalid resource guarantee."""
        manager = QoSManager()
        with pytest.raises(ValueError):
            manager.set_resource_guarantee("test-model", 1.5)
        with pytest.raises(ValueError):
            manager.set_resource_guarantee("test-model", -0.1)
    
    def test_set_resource_limit(self):
        """Test setting resource limit."""
        manager = QoSManager()
        manager.set_resource_limit("test-model", 0.8)
        assert manager.resource_limits["test-model"] == 0.8
    
    def test_submit_request(self):
        """Test submitting a request."""
        manager = QoSManager()
        request = Request(
            request_id="req-1",
            model_id="test-model",
            partition_id=0,
            priority=QoSLevel.MEDIUM,
            timestamp=time.time()
        )
        result = manager.submit_request(request)
        assert result is True
        assert manager.get_queue_depth() == 1
    
    def test_get_next_request(self):
        """Test getting next request."""
        manager = QoSManager()
        
        # Add requests with different priorities
        low_req = Request(
            request_id="req-low",
            model_id="test-model",
            partition_id=0,
            priority=QoSLevel.LOW,
            timestamp=time.time()
        )
        high_req = Request(
            request_id="req-high",
            model_id="test-model",
            partition_id=0,
            priority=QoSLevel.HIGH,
            timestamp=time.time()
        )
        
        manager.submit_request(low_req)
        manager.submit_request(high_req)
        
        # High priority should come first
        next_req = manager.get_next_request()
        assert next_req is not None
        assert next_req.request_id == "req-high"
        assert next_req.priority == QoSLevel.HIGH
    
    def test_record_request_completion(self):
        """Test recording request completion."""
        manager = QoSManager()
        manager.record_request_completion("test-model", 0.5, success=True)
        
        stats = manager.request_stats["test-model"]
        assert stats['total_requests'] == 1
        assert stats['completed_requests'] == 1
        assert stats['failed_requests'] == 0
        assert stats['total_latency'] == 0.5
    
    def test_check_slo_compliance(self):
        """Test SLO compliance checking."""
        manager = QoSManager()
        
        slo = SLO(
            model_id="test-model",
            max_latency_seconds=1.0,
            min_throughput_per_second=10.0
        )
        manager.register_slo(slo)
        
        # Record some requests
        manager.record_request_completion("test-model", 0.3, success=True)
        manager.record_request_completion("test-model", 0.4, success=True)
        manager.record_request_completion("test-model", 0.5, success=True)
        
        is_compliant, metrics = manager.check_slo_compliance("test-model")
        assert isinstance(is_compliant, bool)
        assert isinstance(metrics, dict)
        assert 'avg_latency' in metrics
        assert 'throughput' in metrics
    
    def test_get_queue_depth(self):
        """Test getting queue depth."""
        manager = QoSManager()
        
        assert manager.get_queue_depth() == 0
        
        request = Request(
            request_id="req-1",
            model_id="test-model",
            partition_id=0,
            priority=QoSLevel.MEDIUM,
            timestamp=time.time()
        )
        manager.submit_request(request)
        
        assert manager.get_queue_depth() == 1
        assert manager.get_queue_depth(QoSLevel.MEDIUM) == 1
        assert manager.get_queue_depth(QoSLevel.HIGH) == 0

