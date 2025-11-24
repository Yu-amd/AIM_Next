"""
KServe server for guardrail transformer.

Implements KServe V2 protocol for guardrail integration with AIM.
"""

import logging
import os
from typing import Dict, Any
from guardrails.core.guardrail_service import GuardrailService
from guardrails.policy.policy_manager import PolicyManager
from guardrails.core.guardrail_config import GuardrailConfig
from guardrails.kserve.guardrail_transformer import GuardrailTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize guardrail service
guardrail_service = None
transformer = None


def init_service():
    """Initialize guardrail service for KServe."""
    global guardrail_service, transformer
    
    import yaml
    
    # Load configuration
    config_path = os.environ.get('GUARDRAIL_CONFIG', None)
    guardrail_config_path = os.environ.get('GUARDRAIL_CONFIG_YAML', None)
    enable_metrics = os.environ.get('ENABLE_METRICS', 'false').lower() == 'true'
    
    # Load guardrail configuration
    guardrail_config = None
    if guardrail_config_path:
        try:
            with open(guardrail_config_path, 'r') as f:
                config_dict = yaml.safe_load(f)
                guardrail_config = GuardrailConfig(config_dict.get('guardrails', {}))
        except Exception as e:
            logger.warning(f"Failed to load guardrail config: {e}")
    
    policy_manager = PolicyManager(config_path=config_path)
    guardrail_service = GuardrailService(
        policies=policy_manager.get_policies(),
        enable_metrics=enable_metrics,
        config=guardrail_config
    )
    
    transformer = GuardrailTransformer(guardrail_service)
    
    logger.info("Guardrail transformer service initialized")


def preprocess(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    KServe preprocess hook.
    
    Args:
        inputs: KServe V2 request inputs
        
    Returns:
        Preprocessed inputs
    """
    if not transformer:
        init_service()
    
    return transformer.preprocess(inputs)


def postprocess(inputs: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
    """
    KServe postprocess hook.
    
    Args:
        inputs: Original request inputs
        response: AIM model response
        
    Returns:
        Postprocessed response
    """
    if not transformer:
        init_service()
    
    return transformer.postprocess(inputs, response)


# KServe entry point
if __name__ == '__main__':
    init_service()
    logger.info("KServe guardrail transformer ready")
    # KServe framework will call preprocess/postprocess hooks

