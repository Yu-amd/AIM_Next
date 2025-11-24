"""
Policy/Compliance checker using LLM-as-judge pattern.

Uses a small LLM (Phi-3, Qwen2.5, Llama-3.2) to evaluate content against enterprise policies.
"""

import logging
from typing import Optional, Dict, Any
from guardrails.types.base_checker import BaseChecker
from guardrails.core.guardrail_service import GuardrailResult

logger = logging.getLogger(__name__)


class PolicyComplianceChecker(BaseChecker):
    """Policy compliance checker using LLM-as-judge."""
    
    def __init__(self, model_name: str = "Qwen/Qwen2.5-3B-Instruct", policy_rules: Optional[str] = None):
        """
        Initialize policy compliance checker.
        
        Args:
            model_name: Small LLM for policy judgment
                - "Qwen/Qwen2.5-3B-Instruct" (default)
                - "microsoft/Phi-3-mini-4k-instruct"
                - "meta-llama/Llama-3.2-3B-Instruct"
            policy_rules: Custom policy rules in text format
        """
        self.model = None
        self.tokenizer = None
        self.model_name = model_name
        self.policy_rules = policy_rules or self._default_policy_rules()
        self._load_model()
    
    def _default_policy_rules(self) -> str:
        """Default policy rules."""
        return """
        Policy Rules:
        1. Do not mention confidential product roadmaps or unreleased features
        2. Do not provide financial guidance or investment advice
        3. Do not disclose internal processes or proprietary information
        4. Ensure compliance with regulatory requirements
        5. Maintain professional and appropriate language
        """
    
    def _load_model(self):
        """Load policy judgment model."""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            
            logger.info(f"Loading policy model: {self.model_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True
            )
            
            if not torch.cuda.is_available():
                self.model = self.model.to("cpu")
            
            logger.info("Policy model loaded successfully")
        except ImportError:
            logger.warning("transformers not installed")
            self.model = None
            self.tokenizer = None
        except Exception as e:
            logger.error(f"Failed to load policy model: {e}")
            self.model = None
            self.tokenizer = None
    
    def check(self, content: str, threshold: float = 0.7, **kwargs) -> GuardrailResult:
        """Check content against policy rules."""
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
            
            # Create policy judgment prompt
            prompt = f"""{self.policy_rules}

Content to evaluate:
{content}

Evaluate if this content violates any of the policy rules above. Respond with:
- "COMPLIANT" if content is compliant
- "VIOLATION: [rule number]" if content violates a rule

Response:"""
            
            # Tokenize and generate
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
            if torch.cuda.is_available():
                inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=50,
                    do_sample=False,
                    temperature=0.0
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            response = response[len(prompt):].strip()
            
            # Parse response
            is_compliant = "COMPLIANT" in response.upper() or "compliant" in response.lower()
            is_violation = "VIOLATION" in response.upper() or "violation" in response.lower()
            
            passed = is_compliant and not is_violation
            confidence = 0.9 if is_violation else 0.1
            
            message = "Content is policy compliant" if passed else f"Policy violation detected: {response}"
            
            return GuardrailResult(
                passed=passed, guardrail_type=None, action=None,
                confidence=confidence, message=message,
                details={
                    "model": self.model_name,
                    "response": response,
                    "is_compliant": is_compliant,
                    "is_violation": is_violation
                }
            )
        except Exception as e:
            logger.error(f"Error in policy check: {e}")
            return GuardrailResult(
                passed=True, guardrail_type=None, action=None,
                confidence=0.0, message=f"Error: {str(e)}"
            )
    
    def get_name(self) -> str:
        return "policy_compliance"

