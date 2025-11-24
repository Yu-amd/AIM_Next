"""
Prometheus metrics for guardrail service.

Tracks guardrail checks, blocks, and performance metrics.
"""

import logging
from typing import Dict, Any, Optional

try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("prometheus_client not available. Install with: pip install prometheus-client")

logger = logging.getLogger(__name__)


class GuardrailMetrics:
    """Prometheus metrics exporter for guardrail service."""
    
    def __init__(self, port: int = 9090):
        """
        Initialize metrics exporter.
        
        Args:
            port: Port to expose Prometheus metrics
        """
        if not PROMETHEUS_AVAILABLE:
            raise ImportError("prometheus_client not installed. Install with: pip install prometheus-client")
        
        self.port = port
        self.server_started = False
        
        # Request metrics
        self.requests_total = Counter(
            'guardrail_requests_total',
            'Total number of guardrail checks',
            ['type', 'guardrail_type']
        )
        
        self.requests_blocked = Counter(
            'guardrail_requests_blocked_total',
            'Total number of blocked requests',
            ['type', 'guardrail_type']
        )
        
        # Response metrics
        self.responses_total = Counter(
            'guardrail_responses_total',
            'Total number of response checks',
            ['guardrail_type']
        )
        
        self.responses_blocked = Counter(
            'guardrail_responses_blocked_total',
            'Total number of blocked responses',
            ['guardrail_type']
        )
        
        # Performance metrics
        self.check_duration = Histogram(
            'guardrail_check_duration_seconds',
            'Time taken for guardrail check',
            ['guardrail_type'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
        )
        
        # Confidence metrics
        self.confidence_score = Histogram(
            'guardrail_confidence_score',
            'Confidence score of guardrail detections',
            ['guardrail_type'],
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )
        
        # Model metrics
        self.model_available = Gauge(
            'guardrail_model_available',
            'Whether ML model is available (1) or not (0)',
            ['guardrail_type']
        )
        
        # Latency budget metrics
        self.latency_budget_exceeded = Counter(
            'guardrail_latency_budget_exceeded_total',
            'Total number of times latency budget was exceeded',
            ['use_case']
        )
        
        self.latency_by_use_case = Histogram(
            'guardrail_latency_by_use_case_seconds',
            'Guardrail latency by use case',
            ['use_case'],
            buckets=[0.01, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0, 2.0]
        )
        
        logger.info(f"Guardrail metrics initialized (port: {port})")
    
    def start_server(self) -> None:
        """Start Prometheus metrics HTTP server."""
        if not self.server_started:
            start_http_server(self.port)
            self.server_started = True
            logger.info(f"Prometheus metrics server started on port {self.port}")
            logger.info(f"Metrics available at http://localhost:{self.port}/metrics")
    
    def record_request_check(
        self,
        guardrail_type: str,
        passed: bool,
        confidence: float,
        duration: float,
        use_case: Optional[str] = None
    ) -> None:
        """
        Record a request check.
        
        Args:
            guardrail_type: Type of guardrail
            passed: Whether check passed
            confidence: Confidence score
            duration: Check duration in seconds
            use_case: Optional use case type
        """
        self.requests_total.labels(type='request', guardrail_type=guardrail_type).inc()
        
        if not passed:
            self.requests_blocked.labels(type='request', guardrail_type=guardrail_type).inc()
        
        self.check_duration.labels(guardrail_type=guardrail_type).observe(duration)
        self.confidence_score.labels(guardrail_type=guardrail_type).observe(confidence)
        
        if use_case:
            self.latency_by_use_case.labels(use_case=use_case).observe(duration)
    
    def record_response_check(
        self,
        guardrail_type: str,
        passed: bool,
        confidence: float,
        duration: float
    ) -> None:
        """
        Record a response check.
        
        Args:
            guardrail_type: Type of guardrail
            passed: Whether check passed
            confidence: Confidence score
            duration: Check duration in seconds
        """
        self.responses_total.labels(guardrail_type=guardrail_type).inc()
        
        if not passed:
            self.responses_blocked.labels(guardrail_type=guardrail_type).inc()
        
        self.check_duration.labels(guardrail_type=guardrail_type).observe(duration)
        self.confidence_score.labels(guardrail_type=guardrail_type).observe(confidence)
    
    def set_model_available(self, guardrail_type: str, available: bool) -> None:
        """
        Set model availability status.
        
        Args:
            guardrail_type: Type of guardrail
            available: Whether model is available
        """
        self.model_available.labels(guardrail_type=guardrail_type).set(1 if available else 0)

