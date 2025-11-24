"""
ML-based toxicity detection guardrail using Detoxify.

Production-ready toxicity detection using pre-trained models.
"""

import logging
from typing import Optional
from guardrails.types.base_checker import BaseChecker
from guardrails.core.guardrail_service import GuardrailResult

logger = logging.getLogger(__name__)


class MLToxicityChecker(BaseChecker):
    """ML-based checker for toxic content using Detoxify."""
    
    def __init__(self, model_name: str = "original"):
        """
        Initialize ML toxicity checker.
        
        Args:
            model_name: Detoxify model name ('original', 'unbiased', 'multilingual')
        """
        self.model = None
        self.model_name = model_name
        self._load_model()
    
    def _load_model(self):
        """Load Detoxify model."""
        try:
            from detoxify import Detoxify
            logger.info(f"Loading Detoxify model: {self.model_name}")
            self.model = Detoxify(self.model_name)
            logger.info("Detoxify model loaded successfully")
        except ImportError:
            logger.warning(
                "Detoxify not installed. Install with: pip install detoxify"
            )
            self.model = None
        except Exception as e:
            logger.error(f"Failed to load Detoxify model: {e}")
            self.model = None
    
    def check(self, content: str, threshold: float = 0.7, **kwargs) -> GuardrailResult:
        """
        Check content for toxicity using ML model.
        
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
        
        if not self.model:
            # Fallback: return passed if model not available
            logger.warning("ML model not available, allowing content")
            return GuardrailResult(
                passed=True,
                guardrail_type=None,
                action=None,
                confidence=0.0,
                message="ML model not available"
            )
        
        try:
            # Get toxicity predictions
            results = self.model.predict(content)
            
            # Get maximum toxicity score across all categories
            max_toxicity = max(results.values())
            
            # Get the category with highest score
            max_category = max(results.items(), key=lambda x: x[1])[0]
            
            passed = max_toxicity < threshold
            
            message = "Content is safe"
            if not passed:
                message = f"Toxic content detected: {max_category} (score: {max_toxicity:.3f})"
            
            return GuardrailResult(
                passed=passed,
                guardrail_type=None,
                action=None,
                confidence=float(max_toxicity),
                message=message,
                details={
                    "toxicity_scores": {k: float(v) for k, v in results.items()},
                    "max_category": max_category,
                    "model": self.model_name
                }
            )
        except Exception as e:
            logger.error(f"Error in toxicity check: {e}")
            # On error, allow content but log it
            return GuardrailResult(
                passed=True,
                guardrail_type=None,
                action=None,
                confidence=0.0,
                message=f"Error during check: {str(e)}"
            )
    
    def get_name(self) -> str:
        """Get checker name."""
        return "ml_toxicity"

