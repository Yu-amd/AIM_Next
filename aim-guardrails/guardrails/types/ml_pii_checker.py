"""
ML-based PII detection guardrail using Presidio.

Production-ready PII detection and redaction using Microsoft Presidio.
"""

import logging
from typing import Optional, Dict, List
from guardrails.types.base_checker import BaseChecker
from guardrails.core.guardrail_service import GuardrailResult

logger = logging.getLogger(__name__)


class MLPIIChecker(BaseChecker):
    """ML-based checker for PII using Presidio."""
    
    def __init__(self):
        """Initialize ML PII checker."""
        self.analyzer = None
        self.anonymizer = None
        self._load_models()
    
    def _load_models(self):
        """Load Presidio analyzer and anonymizer."""
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine
            
            logger.info("Loading Presidio models...")
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            logger.info("Presidio models loaded successfully")
        except ImportError:
            logger.warning(
                "Presidio not installed. Install with: pip install presidio-analyzer presidio-anonymizer"
            )
            self.analyzer = None
            self.anonymizer = None
        except Exception as e:
            logger.error(f"Failed to load Presidio models: {e}")
            self.analyzer = None
            self.anonymizer = None
    
    def check(self, content: str, threshold: float = 0.8, **kwargs) -> GuardrailResult:
        """
        Check content for PII using ML model.
        
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
        
        if not self.analyzer or not self.anonymizer:
            # Fallback: return passed if model not available
            logger.warning("ML models not available, allowing content")
            return GuardrailResult(
                passed=True,
                guardrail_type=None,
                action=None,
                confidence=0.0,
                message="ML models not available"
            )
        
        try:
            # Analyze for PII
            results = self.analyzer.analyze(
                text=content,
                language='en'
            )
            
            if not results:
                return GuardrailResult(
                    passed=True,
                    guardrail_type=None,
                    action=None,
                    confidence=0.0,
                    message="No PII detected"
                )
            
            # Calculate confidence based on number and confidence of detections
            total_confidence = sum(r.score for r in results)
            avg_confidence = total_confidence / len(results) if results else 0.0
            confidence = min(avg_confidence * len(results) * 0.2, 1.0)  # Scale based on count
            
            passed = confidence < threshold
            
            # Anonymize if PII found
            redacted_content = None
            if results:
                anonymized = self.anonymizer.anonymize(
                    text=content,
                    analyzer_results=results
                )
                redacted_content = anonymized.text
            
            # Group by entity type
            pii_by_type = {}
            for result in results:
                entity_type = result.entity_type
                if entity_type not in pii_by_type:
                    pii_by_type[entity_type] = []
                pii_by_type[entity_type].append({
                    "text": content[result.start:result.end],
                    "score": result.score
                })
            
            message = "No PII detected"
            if not passed:
                pii_types = list(pii_by_type.keys())
                message = f"PII detected: {', '.join(pii_types)} ({len(results)} entities)"
            
            return GuardrailResult(
                passed=passed,
                guardrail_type=None,
                action=None,
                confidence=confidence,
                message=message,
                details={
                    "detected_pii": pii_by_type,
                    "entity_count": len(results),
                    "entities": [
                        {
                            "type": r.entity_type,
                            "text": content[r.start:r.end],
                            "score": r.score,
                            "start": r.start,
                            "end": r.end
                        }
                        for r in results
                    ]
                },
                redacted_content=redacted_content if results else None
            )
        except Exception as e:
            logger.error(f"Error in PII check: {e}")
            return GuardrailResult(
                passed=True,
                guardrail_type=None,
                action=None,
                confidence=0.0,
                message=f"Error during check: {str(e)}"
            )
    
    def get_name(self) -> str:
        """Get checker name."""
        return "ml_pii"

