"""
Enhanced prompt injection detection using semantic similarity and heuristics.

Production-ready prompt injection detection combining pattern matching
with semantic analysis.
"""

import logging
import re
from typing import List, Dict, Any
from guardrails.types.base_checker import BaseChecker
from guardrails.core.guardrail_service import GuardrailResult

logger = logging.getLogger(__name__)


class EnhancedPromptInjectionChecker(BaseChecker):
    """Enhanced checker for prompt injection attacks."""
    
    def __init__(self):
        """Initialize enhanced prompt injection checker."""
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
            r'roleplay',
            r'pretend\s+you\s+are',
            r'act\s+as\s+if',
        ]
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.injection_patterns]
        
        # Suspicious indicators
        self.suspicious_indicators = [
            'ignore previous',
            'forget everything',
            'new instructions',
            'system prompt',
            'jailbreak',
            'override safety',
            'disable safety',
            'remove restrictions',
            'act as',
            'pretend to be',
            'roleplay as',
        ]
        
        # Try to load sentence transformer for semantic similarity (optional)
        self.similarity_model = None
        self._load_similarity_model()
        
        logger.info("Enhanced prompt injection checker initialized")
    
    def _load_similarity_model(self):
        """Load optional semantic similarity model."""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading sentence transformer for semantic similarity...")
            # Use a small, fast model
            self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Similarity model loaded")
        except ImportError:
            logger.debug("Sentence transformers not available (optional)")
            self.similarity_model = None
        except Exception as e:
            logger.debug(f"Could not load similarity model: {e}")
            self.similarity_model = None
    
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
        
        content_lower = content.lower()
        matches = []
        confidence = 0.0
        
        # Pattern matching
        for pattern in self.compiled_patterns:
            if pattern.search(content):
                matches.append(pattern.pattern)
                confidence += 0.15
        
        # Suspicious indicator matching
        indicator_count = 0
        for indicator in self.suspicious_indicators:
            if indicator in content_lower:
                indicator_count += 1
                matches.append(f"indicator: {indicator}")
        
        if indicator_count > 0:
            confidence += min(indicator_count * 0.1, 0.3)
        
        # Semantic similarity check (if model available)
        if self.similarity_model:
            try:
                known_injections = [
                    "ignore all previous instructions",
                    "forget everything and act as",
                    "system: you are now",
                    "bypass safety restrictions",
                ]
                
                content_embedding = self.similarity_model.encode([content])[0]
                injection_embeddings = self.similarity_model.encode(known_injections)
                
                from sklearn.metrics.pairwise import cosine_similarity
                similarities = cosine_similarity([content_embedding], injection_embeddings)[0]
                max_similarity = float(max(similarities))
                
                if max_similarity > 0.7:
                    confidence += max_similarity * 0.2
                    matches.append(f"semantic_similarity: {max_similarity:.2f}")
            except Exception as e:
                logger.debug(f"Semantic similarity check failed: {e}")
        
        # Additional heuristics
        # Check for unusual capitalization patterns
        if content != content.lower() and content != content.upper():
            caps_ratio = sum(1 for c in content if c.isupper()) / len(content) if content else 0
            if 0.3 < caps_ratio < 0.7:  # Mixed case might indicate injection
                confidence += 0.05
        
        # Check for multiple instruction-like phrases
        instruction_phrases = ['instruction', 'prompt', 'system', 'command', 'directive']
        phrase_count = sum(1 for phrase in instruction_phrases if phrase in content_lower)
        if phrase_count >= 2:
            confidence += 0.1
        
        confidence = min(confidence, 1.0)
        passed = confidence < threshold
        
        message = "No prompt injection detected"
        if not passed:
            message = f"Potential prompt injection detected (confidence: {confidence:.2f}, patterns: {len(matches)})"
        
        return GuardrailResult(
            passed=passed,
            guardrail_type=None,
            action=None,
            confidence=confidence,
            message=message,
            details={
                "matched_patterns": matches[:10],  # Limit to first 10
                "content_length": len(content),
                "suspicious_indicators": indicator_count,
                "has_semantic_match": any("semantic_similarity" in m for m in matches)
            }
        )
    
    def get_name(self) -> str:
        """Get checker name."""
        return "enhanced_prompt_injection"

