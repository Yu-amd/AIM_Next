"""
Prompt injection detection using protectai/deberta-v3-base-prompt-injection.

Production-ready prompt injection detection using specialized DeBERTa models.
"""

import logging
from typing import Optional
from guardrails.types.base_checker import BaseChecker
from guardrails.core.guardrail_service import GuardrailResult

logger = logging.getLogger(__name__)


class ProtectAIPromptInjectionChecker(BaseChecker):
    """Prompt injection checker using protectai DeBERTa models."""
    
    def __init__(self, model_name: str = "protectai/deberta-v3-base-prompt-injection-v2"):
        """
        Initialize ProtectAI prompt injection checker.
        
        Args:
            model_name: HuggingFace model name
                - "protectai/deberta-v3-base-prompt-injection-v2" (default, latest)
                - "protectai/deberta-v3-base-prompt-injection" (original)
        """
        self.model = None
        self.tokenizer = None
        self.model_name = model_name
        self._load_model()
    
    def _load_model(self):
        """Load ProtectAI model."""
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            
            logger.info(f"Loading ProtectAI model: {self.model_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True
            )
            
            if not torch.cuda.is_available():
                self.model = self.model.to("cpu")
            
            self.model.eval()
            logger.info("ProtectAI model loaded successfully")
        except ImportError:
            logger.warning(
                "transformers not installed. Install with: pip install transformers torch"
            )
            self.model = None
            self.tokenizer = None
        except Exception as e:
            logger.error(f"Failed to load ProtectAI model: {e}")
            self.model = None
            self.tokenizer = None
    
    def check(self, content: str, threshold: float = 0.75, **kwargs) -> GuardrailResult:
        """
        Check content for prompt injection.
        
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
        
        if not self.model or not self.tokenizer:
            logger.warning("ProtectAI model not available, allowing content")
            return GuardrailResult(
                passed=True,
                guardrail_type=None,
                action=None,
                confidence=0.0,
                message="Model not available"
            )
        
        try:
            import torch
            
            # Tokenize
            inputs = self.tokenizer(
                content,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )
            
            if torch.cuda.is_available():
                inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
            
            # Get prediction
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)
                
                # Get probability of injection (class 1)
                injection_prob = float(probs[0][1])
            
            passed = injection_prob < threshold
            confidence = injection_prob
            
            message = "No prompt injection detected"
            if not passed:
                message = f"Prompt injection detected (confidence: {injection_prob:.3f})"
            
            return GuardrailResult(
                passed=passed,
                guardrail_type=None,
                action=None,
                confidence=confidence,
                message=message,
                details={
                    "model": self.model_name,
                    "injection_probability": injection_prob,
                    "threshold": threshold
                }
            )
        except Exception as e:
            logger.error(f"Error in ProtectAI check: {e}")
            return GuardrailResult(
                passed=True,
                guardrail_type=None,
                action=None,
                confidence=0.0,
                message=f"Error during check: {str(e)}"
            )
    
    def get_name(self) -> str:
        """Get checker name."""
        return "protectai_prompt_injection"

