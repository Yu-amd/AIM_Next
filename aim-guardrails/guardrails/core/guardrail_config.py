"""
Guardrail configuration system.

Allows configuration of which models to use for each guardrail type.
"""

import logging
from typing import Dict, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class GuardrailModelType(Enum):
    """Available model types for each guardrail."""
    # Toxicity models
    DETOXIFY = "detoxify"
    ROBERTA_TOXICITY = "roberta_toxicity"
    XLM_TOXICITY = "xlm_toxicity"
    
    # PII models
    PRESIDIO = "presidio"
    PIIRANHA = "piiranha"
    AB_AI_PII = "ab_ai_pii"
    PHI3_PII = "phi3_pii"
    
    # Prompt injection models
    PROTECTAI_DEBERTA = "protectai_deberta"
    ENHANCED_PATTERN = "enhanced_pattern"
    
    # All-in-one judges
    LLAMA_GUARD = "llama_guard"
    GRANITE_GUARDIAN = "granite_guardian"
    
    # Policy/Compliance
    POLICY_LLM = "policy_llm"
    
    # Secrets
    SECRET_SCANNER = "secret_scanner"


class GuardrailConfig:
    """Configuration for guardrail service."""
    
    def __init__(self, config_dict: Optional[Dict] = None):
        """
        Initialize guardrail configuration.
        
        Args:
            config_dict: Configuration dictionary with model selections
        """
        self.config = config_dict or self._default_config()
    
    def _default_config(self) -> Dict:
        """Default configuration matching user requirements."""
        return {
            "toxicity": {
                "model": GuardrailModelType.ROBERTA_TOXICITY.value,
                "fallback": GuardrailModelType.DETOXIFY.value,
                "pre_filter": True,
                "post_filter": True,
            },
            "pii": {
                "model": GuardrailModelType.PIIRANHA.value,
                "fallback": GuardrailModelType.PRESIDIO.value,
                "pre_filter": True,  # Check input for disallowed PII
                "post_filter": True,  # Redact PII in output
            },
            "prompt_injection": {
                "model": GuardrailModelType.PROTECTAI_DEBERTA.value,
                "fallback": GuardrailModelType.ENHANCED_PATTERN.value,
                "pre_filter": True,  # Only check input
                "post_filter": False,
            },
            "policy_compliance": {
                "model": GuardrailModelType.POLICY_LLM.value,
                "pre_filter": False,
                "post_filter": True,  # Check output against policies
            },
            "secrets": {
                "model": GuardrailModelType.SECRET_SCANNER.value,
                "pre_filter": True,
                "post_filter": True,  # Especially for code models
            },
            "all_in_one_judge": {
                "model": GuardrailModelType.LLAMA_GUARD.value,
                "pre_filter": True,
                "post_filter": True,
                "optional": True,  # Can be used alongside specific checkers
            }
        }
    
    def get_model_for_type(self, guardrail_type: str) -> str:
        """Get model name for guardrail type."""
        return self.config.get(guardrail_type, {}).get("model", "")
    
    def should_pre_filter(self, guardrail_type: str) -> bool:
        """Check if guardrail should run on input."""
        return self.config.get(guardrail_type, {}).get("pre_filter", False)
    
    def should_post_filter(self, guardrail_type: str) -> bool:
        """Check if guardrail should run on output."""
        return self.config.get(guardrail_type, {}).get("post_filter", False)

