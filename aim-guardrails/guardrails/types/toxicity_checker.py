"""
Toxicity detection guardrail.

Detects toxic, harmful, or inappropriate content in prompts and responses.
"""

import re
import logging
from typing import List, Dict, Any
from guardrails.types.base_checker import BaseChecker
from guardrails.core.guardrail_service import GuardrailResult

logger = logging.getLogger(__name__)


class ToxicityChecker(BaseChecker):
    """Checker for toxic content."""
    
    def __init__(self):
        """Initialize toxicity checker."""
        # Common toxic patterns (simplified - in production, use ML models)
        self.toxic_patterns = [
            r'\b(kill|murder|suicide|harm|violence|hate|racist|sexist)\b',
            r'\b(threat|attack|destroy|hurt|abuse)\b',
            # Add more patterns as needed
        ]
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.toxic_patterns]
        
        logger.info("Toxicity checker initialized")
    
    def check(self, content: str, threshold: float = 0.7, **kwargs) -> GuardrailResult:
        """
        Check content for toxicity.
        
        Args:
            content: Content to check
            threshold: Confidence threshold
            **kwargs: Additional parameters
            
        Returns:
            GuardrailResult
        """
        if not content:
            return GuardrailResult(
                passed=True,
                guardrail_type=None,  # Will be set by service
                action=None,
                confidence=0.0,
                message="Empty content"
            )
        
        # Check for toxic patterns
        matches = []
        for pattern in self.compiled_patterns:
            if pattern.search(content):
                matches.append(pattern.pattern)
        
        # Calculate confidence based on matches
        confidence = min(len(matches) * 0.3, 1.0) if matches else 0.0
        
        passed = confidence < threshold
        
        message = "Content is safe"
        if not passed:
            message = f"Toxic content detected (patterns: {', '.join(matches)})"
        
        return GuardrailResult(
            passed=passed,
            guardrail_type=None,  # Will be set by service
            action=None,  # Will be set by service
            confidence=confidence,
            message=message,
            details={
                "matched_patterns": matches,
                "content_length": len(content)
            }
        )
    
    def get_name(self) -> str:
        """Get checker name."""
        return "toxicity"

