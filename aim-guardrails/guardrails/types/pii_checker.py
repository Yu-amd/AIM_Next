"""
PII (Personally Identifiable Information) detection guardrail.

Detects and optionally redacts PII such as emails, phone numbers, SSNs, etc.
"""

import re
import logging
from typing import List, Dict, Any
from guardrails.types.base_checker import BaseChecker
from guardrails.core.guardrail_service import GuardrailResult

logger = logging.getLogger(__name__)


class PIIChecker(BaseChecker):
    """Checker for PII (Personally Identifiable Information)."""
    
    def __init__(self):
        """Initialize PII checker."""
        # PII patterns
        self.pii_patterns = {
            "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            "phone": re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
            "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            "credit_card": re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'),
            "ip_address": re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),
        }
        
        logger.info("PII checker initialized")
    
    def check(self, content: str, threshold: float = 0.8, **kwargs) -> GuardrailResult:
        """
        Check content for PII.
        
        Args:
            content: Content to check
            threshold: Confidence threshold
            **kwargs: Additional parameters
            
        Returns:
            GuardrailResult with redacted_content if PII found
        """
        if not content:
            return GuardrailResult(
                passed=True,
                guardrail_type=None,
                action=None,
                confidence=0.0,
                message="Empty content"
            )
        
        detected_pii = {}
        redacted_content = content
        
        # Check for each PII type
        for pii_type, pattern in self.pii_patterns.items():
            matches = pattern.findall(content)
            if matches:
                detected_pii[pii_type] = matches
                # Redact PII
                for match in matches:
                    redacted_content = redacted_content.replace(match, f"[{pii_type.upper()}_REDACTED]")
        
        # Calculate confidence
        confidence = min(len(detected_pii) * 0.4, 1.0) if detected_pii else 0.0
        passed = confidence < threshold
        
        message = "No PII detected"
        if not passed:
            pii_types = list(detected_pii.keys())
            message = f"PII detected: {', '.join(pii_types)}"
        
        return GuardrailResult(
            passed=passed,
            guardrail_type=None,
            action=None,
            confidence=confidence,
            message=message,
            details={
                "detected_pii": detected_pii,
                "pii_count": sum(len(v) for v in detected_pii.values())
            },
            redacted_content=redacted_content if detected_pii else None
        )
    
    def get_name(self) -> str:
        """Get checker name."""
        return "pii"

