"""
Llama Guard-based all-in-one safety judge.

Uses Meta's Llama Guard models for comprehensive safety classification.
Supports Llama Guard 2, 3, and 4.
"""

import logging
from typing import Optional, Dict, Any, List
from guardrails.types.base_checker import BaseChecker
from guardrails.core.guardrail_service import GuardrailResult

logger = logging.getLogger(__name__)


class LlamaGuardChecker(BaseChecker):
    """All-in-one safety judge using Llama Guard models."""
    
    def __init__(self, model_name: str = "meta-llama/LlamaGuard-3-8B"):
        """
        Initialize Llama Guard checker.
        
        Args:
            model_name: HuggingFace model name
                - "meta-llama/LlamaGuard-3-8B" (default, Llama 3.1-based)
                - "meta-llama/LlamaGuard-3-1B" (smaller, faster)
                - "meta-llama/LlamaGuard-2-8B" (Llama 3-based)
                - "meta-llama/Llama-Guard-2-8B" (original Llama Guard 2)
        """
        self.model = None
        self.tokenizer = None
        self.model_name = model_name
        self._load_model()
    
    def _load_model(self):
        """Load Llama Guard model."""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            
            logger.info(f"Loading Llama Guard model: {self.model_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True
            )
            
            if not torch.cuda.is_available():
                self.model = self.model.to("cpu")
            
            logger.info("Llama Guard model loaded successfully")
        except ImportError:
            logger.warning(
                "transformers not installed. Install with: pip install transformers torch"
            )
            self.model = None
            self.tokenizer = None
        except Exception as e:
            logger.error(f"Failed to load Llama Guard model: {e}")
            self.model = None
            self.tokenizer = None
    
    def check(self, content: str, threshold: float = 0.7, **kwargs) -> GuardrailResult:
        """
        Check content using Llama Guard.
        
        Args:
            content: Content to check
            threshold: Confidence threshold (not directly used, Llama Guard returns binary)
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
            logger.warning("Llama Guard model not available, allowing content")
            return GuardrailResult(
                passed=True,
                guardrail_type=None,
                action=None,
                confidence=0.0,
                message="Model not available"
            )
        
        try:
            import torch
            
            # Format prompt for Llama Guard
            # Llama Guard 3 uses a specific format
            if "LlamaGuard-3" in self.model_name:
                prompt = f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{content}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
            else:
                # Llama Guard 2 format
                prompt = f"Task: Check if there is unsafe content in '{content}' according to the safety policy.\n\n"
            
            # Tokenize and generate
            inputs = self.tokenizer(prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=100,
                    do_sample=False,
                    temperature=0.0
                )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Parse Llama Guard response
            # Response format: "safe" or "unsafe" with categories
            is_safe = "safe" in response.lower() or "O1" in response  # O1 = safe in Llama Guard 3
            is_unsafe = "unsafe" in response.lower() or "O2" in response  # O2 = unsafe
            
            # Extract categories if present
            categories = []
            if not is_safe:
                # Try to extract category codes (S1, S2, etc. for Llama Guard 3)
                import re
                category_pattern = r'[OS]\d+'
                categories = re.findall(category_pattern, response)
            
            passed = is_safe and not is_unsafe
            confidence = 0.9 if is_unsafe else 0.1  # High confidence for binary classification
            
            message = "Content is safe" if passed else f"Unsafe content detected: {', '.join(categories) if categories else 'unsafe'}"
            
            return GuardrailResult(
                passed=passed,
                guardrail_type=None,
                action=None,
                confidence=confidence,
                message=message,
                details={
                    "model": self.model_name,
                    "response": response,
                    "categories": categories,
                    "is_safe": is_safe,
                    "is_unsafe": is_unsafe
                }
            )
        except Exception as e:
            logger.error(f"Error in Llama Guard check: {e}")
            return GuardrailResult(
                passed=True,
                guardrail_type=None,
                action=None,
                confidence=0.0,
                message=f"Error during check: {str(e)}"
            )
    
    def get_name(self) -> str:
        """Get checker name."""
        return "llama_guard"

