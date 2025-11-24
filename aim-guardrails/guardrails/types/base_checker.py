"""
Base class for guardrail checkers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from guardrails.core.guardrail_service import GuardrailResult


class BaseChecker(ABC):
    """Base class for guardrail checkers."""
    
    @abstractmethod
    def check(self, content: str, threshold: float = 0.7, **kwargs) -> GuardrailResult:
        """
        Check content against the guardrail.
        
        Args:
            content: Content to check
            threshold: Confidence threshold
            **kwargs: Additional parameters
            
        Returns:
            GuardrailResult
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of this checker."""
        pass

