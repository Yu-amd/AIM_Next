"""
Policy manager for guardrail configurations.

Loads and manages guardrail policies from configuration files.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from guardrails.core.guardrail_service import GuardrailPolicy, GuardrailType, GuardrailAction

logger = logging.getLogger(__name__)


class PolicyManager:
    """Manages guardrail policies."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize policy manager.
        
        Args:
            config_path: Path to policy configuration file
        """
        self.config_path = config_path
        self.policies: List[GuardrailPolicy] = []
        
        if config_path:
            self.load_from_file(config_path)
        else:
            self.policies = self._default_policies()
    
    def _default_policies(self) -> List[GuardrailPolicy]:
        """Create default policies."""
        return [
            GuardrailPolicy(
                guardrail_type=GuardrailType.TOXICITY,
                enabled=True,
                action=GuardrailAction.BLOCK,
                threshold=0.7
            ),
            GuardrailPolicy(
                guardrail_type=GuardrailType.PII,
                enabled=True,
                action=GuardrailAction.REDACT,
                threshold=0.8
            ),
            GuardrailPolicy(
                guardrail_type=GuardrailType.PROMPT_INJECTION,
                enabled=True,
                action=GuardrailAction.BLOCK,
                threshold=0.75
            ),
        ]
    
    def load_from_file(self, config_path: str) -> bool:
        """
        Load policies from a JSON configuration file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            True if loaded successfully
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            self.policies = []
            for policy_config in config.get('policies', []):
                policy = GuardrailPolicy(
                    guardrail_type=GuardrailType(policy_config['type']),
                    enabled=policy_config.get('enabled', True),
                    action=GuardrailAction(policy_config.get('action', 'block')),
                    threshold=policy_config.get('threshold', 0.7),
                    custom_rules=policy_config.get('custom_rules')
                )
                self.policies.append(policy)
            
            logger.info(f"Loaded {len(self.policies)} policies from {config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load policies from {config_path}: {e}")
            self.policies = self._default_policies()
            return False
    
    def save_to_file(self, config_path: str) -> bool:
        """
        Save policies to a JSON configuration file.
        
        Args:
            config_path: Path to save configuration
            
        Returns:
            True if saved successfully
        """
        try:
            config = {
                "policies": [
                    {
                        "type": policy.guardrail_type.value,
                        "enabled": policy.enabled,
                        "action": policy.action.value,
                        "threshold": policy.threshold,
                        "custom_rules": policy.custom_rules
                    }
                    for policy in self.policies
                ]
            }
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Saved {len(self.policies)} policies to {config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save policies to {config_path}: {e}")
            return False
    
    def get_policies(self) -> List[GuardrailPolicy]:
        """Get all policies."""
        return self.policies
    
    def get_policy(self, guardrail_type: GuardrailType) -> Optional[GuardrailPolicy]:
        """Get a specific policy."""
        for policy in self.policies:
            if policy.guardrail_type == guardrail_type:
                return policy
        return None

