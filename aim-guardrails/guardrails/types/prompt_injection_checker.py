"""
Prompt injection detection guardrail.

Detects attempts to inject malicious prompts or override system instructions.
"""

import re
import logging
from typing import List, Dict, Any
from guardrails.types.base_checker import BaseChecker
from guardrails.core.guardrail_service import GuardrailResult

logger = logging.getLogger(__name__)


class PromptInjectionChecker(BaseChecker):
    """Checker for prompt injection attacks."""
    
    def __init__(self):
        """Initialize prompt injection checker."""
        # Common prompt injection patterns
        self.injection_patterns = [
            r'ignore\s+(previous|above|all)\s+(instructions|prompts|rules)',
            r'forget\s+(everything|all|previous)',
            r'you\s+are\s+now\s+(a|an)\s+',
            r'system\s*:\s*',
            r'<\|system\|>',
            r'<\|assistant\|>',
            r'\[INST\]',
            r'###\s*(system|instruction|prompt)\s*:',
            r'override',
            r'bypass',
            r'jailbreak',
        ]
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.injection_patterns]
        
        logger.info("Prompt injection checker initialized")
    
    def check(self, content: str, threshold: float = 0.75, **kwargs) -> GuardrailResult:
        """
        Check content for prompt injection attempts.
        
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
                guardrail_type=None,
                action=None,
                confidence=0.0,
                message="Empty content"
            )
        
        # Check for injection patterns
        matches = []
        for pattern in self.compiled_patterns:
            if pattern.search(content):
                matches.append(pattern.pattern)
        
        # Calculate confidence
        confidence = min(len(matches) * 0.25, 1.0) if matches else 0.0
        
        # Additional heuristics
        content_lower = content.lower()
        suspicious_indicators = [
            'ignore previous',
            'forget everything',
            'new instructions',
            'system prompt',
            'jailbreak',
        ]
        
        for indicator in suspicious_indicators:
            if indicator in content_lower:
                confidence = min(confidence + 0.2, 1.0)
                matches.append(f"indicator: {indicator}")
        
        passed = confidence < threshold
        
        message = "No prompt injection detected"
        if not passed:
            message = f"Potential prompt injection detected (patterns: {len(matches)})"
        
        return GuardrailResult(
            passed=passed,
            guardrail_type=None,
            action=None,
            confidence=confidence,
            message=message,
            details={
                "matched_patterns": matches[:5],  # Limit to first 5
                "content_length": len(content),
                "suspicious_indicators": len([i for i in suspicious_indicators if i in content_lower])
            }
        )
    
    def get_name(self) -> str:
        """Get checker name."""
        return "prompt_injection"

