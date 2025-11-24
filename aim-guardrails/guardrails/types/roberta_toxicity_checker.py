"""
RoBERTa-based toxicity classifier.

Uses s-nlp/roberta_toxicity_classifier for fast, accurate toxicity detection.
"""

import logging
from typing import Optional
from guardrails.types.base_checker import BaseChecker
from guardrails.core.guardrail_service import GuardrailResult

logger = logging.getLogger(__name__)


class RoBERTaToxicityChecker(BaseChecker):
    """RoBERTa-based toxicity checker."""
    
    def __init__(self, model_name: str = "s-nlp/roberta_toxicity_classifier"):
        """
        Initialize RoBERTa toxicity checker.
        
        Args:
            model_name: HuggingFace model name
                - "s-nlp/roberta_toxicity_classifier" (default)
                - "textdetox/xlmr-large-toxicity-classifier" (multilingual)
        """
        self.model = None
        self.tokenizer = None
        self.model_name = model_name
        self._load_model()
    
    def _load_model(self):
        """Load RoBERTa toxicity model."""
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            
            logger.info(f"Loading RoBERTa toxicity model: {self.model_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            
            if not torch.cuda.is_available():
                self.model = self.model.to("cpu")
            
            self.model.eval()
            logger.info("RoBERTa toxicity model loaded successfully")
        except ImportError:
            logger.warning("transformers not installed")
            self.model = None
            self.tokenizer = None
        except Exception as e:
            logger.error(f"Failed to load RoBERTa model: {e}")
            self.model = None
            self.tokenizer = None
    
    def check(self, content: str, threshold: float = 0.7, **kwargs) -> GuardrailResult:
        """Check content for toxicity."""
        if not content:
            return GuardrailResult(
                passed=True, guardrail_type=None, action=None,
                confidence=0.0, message="Empty content"
            )
        
        if not self.model or not self.tokenizer:
            logger.warning("Model not available, allowing content")
            return GuardrailResult(
                passed=True, guardrail_type=None, action=None,
                confidence=0.0, message="Model not available"
            )
        
        try:
            import torch
            
            inputs = self.tokenizer(
                content, return_tensors="pt", truncation=True,
                max_length=512, padding=True
            )
            
            if torch.cuda.is_available():
                inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)
                toxicity_prob = float(probs[0][1])  # Assuming class 1 is toxic
            
            passed = toxicity_prob < threshold
            
            message = "Content is safe" if passed else f"Toxic content detected (score: {toxicity_prob:.3f})"
            
            return GuardrailResult(
                passed=passed, guardrail_type=None, action=None,
                confidence=toxicity_prob, message=message,
                details={"model": self.model_name, "toxicity_score": toxicity_prob}
            )
        except Exception as e:
            logger.error(f"Error in toxicity check: {e}")
            return GuardrailResult(
                passed=True, guardrail_type=None, action=None,
                confidence=0.0, message=f"Error: {str(e)}"
            )
    
    def get_name(self) -> str:
        return "roberta_toxicity"

