"""
Core guardrail service for AI inference safety.

Provides a unified interface for multiple guardrail types including
toxicity detection, PII detection, and prompt injection detection.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

# Optional latency budget import
try:
    from guardrails.core.latency_budget import LatencyBudgetManager, UseCase
    LATENCY_BUDGET_AVAILABLE = True
except ImportError:
    LATENCY_BUDGET_AVAILABLE = False
    LatencyBudgetManager = None
    UseCase = None

# Optional metrics import
try:
    from guardrails.monitoring.metrics import GuardrailMetrics
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    GuardrailMetrics = None


class GuardrailType(Enum):
    """Types of guardrails available."""
    TOXICITY = "toxicity"
    PII = "pii"
    PROMPT_INJECTION = "prompt_injection"
    POLICY_COMPLIANCE = "policy_compliance"
    SECRETS = "secrets"
    ALL_IN_ONE = "all_in_one"
    CUSTOM = "custom"


class GuardrailAction(Enum):
    """Actions to take when a guardrail is triggered."""
    ALLOW = "allow"  # Allow (below threshold)
    BLOCK = "block"  # Block the request/response (above hard threshold)
    ALLOW_WITH_WARNING = "allow_with_warning"  # Soft fail: log, watermark, or weaken response
    REDACT = "redact"  # Remove sensitive content
    MODIFY = "modify"  # Modify the content


@dataclass
class GuardrailResult:
    """Result of a guardrail check."""
    passed: bool
    guardrail_type: GuardrailType
    action: GuardrailAction
    confidence: float
    message: str
    details: Optional[Dict[str, Any]] = None
    redacted_content: Optional[str] = None


@dataclass
class GuardrailPolicy:
    """Policy configuration for a guardrail."""
    guardrail_type: GuardrailType
    enabled: bool = True
    action: GuardrailAction = GuardrailAction.BLOCK
    threshold: float = 0.7  # Confidence threshold
    custom_rules: Optional[Dict[str, Any]] = None


class GuardrailService:
    """Core guardrail service for AI inference safety."""
    
    def __init__(self, policies: Optional[List[GuardrailPolicy]] = None, enable_metrics: bool = False, config: Optional[Any] = None):
        """
        Initialize guardrail service.
        
        Args:
            policies: List of guardrail policies to apply
            enable_metrics: Enable Prometheus metrics export
            config: Guardrail configuration (model selection)
        """
        from guardrails.core.guardrail_config import GuardrailConfig
        
        self.policies = policies or self._default_policies()
        self.guardrails = {}
        self.config = config or GuardrailConfig()
        self.metrics: Optional[GuardrailMetrics] = None
        self.policy_checker = None
        self.all_in_one_judge = None
        self.latency_budget_manager = None
        
        if LATENCY_BUDGET_AVAILABLE:
            self.latency_budget_manager = LatencyBudgetManager()
        
        if enable_metrics and METRICS_AVAILABLE:
            try:
                self.metrics = GuardrailMetrics(port=9090)
                self.metrics.start_server()
                logger.info("Metrics enabled")
            except Exception as e:
                logger.warning(f"Failed to start metrics: {e}")
        
        self._initialize_guardrails(self.config)
        
        # Update model availability metrics
        if self.metrics:
            for gr_type, checker in self.guardrails.items():
                model_available = hasattr(checker, 'model') and checker.model is not None
                self.metrics.set_model_available(gr_type.value, model_available)
        
        logger.info(f"Guardrail service initialized with {len(self.policies)} policies")
    
    def _default_policies(self) -> List[GuardrailPolicy]:
        """Create default guardrail policies."""
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
    
    def _initialize_guardrails(self, config: Optional[Any] = None):
        """Initialize guardrail checkers based on configuration."""
        from guardrails.core.guardrail_config import GuardrailConfig, GuardrailModelType
        
        if config is None:
            config = GuardrailConfig()
        
        logger.info("Initializing guardrails based on configuration")
        
        # Initialize based on config
        self._init_toxicity_checker(config)
        self._init_pii_checker(config)
        self._init_prompt_injection_checker(config)
        self._init_secret_scanner(config)
        self._init_policy_checker(config)
        self._init_all_in_one_judge(config)
    
    def _init_toxicity_checker(self, config):
        """Initialize toxicity checker."""
        from guardrails.core.guardrail_config import GuardrailModelType
        model_type = config.get_model_for_type("toxicity")
        try:
            if model_type == GuardrailModelType.ROBERTA_TOXICITY.value:
                from guardrails.types.roberta_toxicity_checker import RoBERTaToxicityChecker
                self.guardrails[GuardrailType.TOXICITY] = RoBERTaToxicityChecker()
            elif model_type == GuardrailModelType.DETOXIFY.value:
                from guardrails.types.ml_toxicity_checker import MLToxicityChecker
                self.guardrails[GuardrailType.TOXICITY] = MLToxicityChecker()
            else:
                # Fallback
                from guardrails.types.ml_toxicity_checker import MLToxicityChecker
                self.guardrails[GuardrailType.TOXICITY] = MLToxicityChecker()
        except Exception as e:
            logger.warning(f"Failed to load toxicity model, using fallback: {e}")
            from guardrails.types.toxicity_checker import ToxicityChecker
            self.guardrails[GuardrailType.TOXICITY] = ToxicityChecker()
    
    def _init_pii_checker(self, config):
        """Initialize PII checker."""
        from guardrails.core.guardrail_config import GuardrailModelType
        model_type = config.get_model_for_type("pii")
        try:
            if model_type == GuardrailModelType.PIIRANHA.value:
                from guardrails.types.piiranha_pii_checker import PiiranhaPIIChecker
                self.guardrails[GuardrailType.PII] = PiiranhaPIIChecker()
            elif model_type == GuardrailModelType.PRESIDIO.value:
                from guardrails.types.ml_pii_checker import MLPIIChecker
                self.guardrails[GuardrailType.PII] = MLPIIChecker()
            else:
                from guardrails.types.ml_pii_checker import MLPIIChecker
                self.guardrails[GuardrailType.PII] = MLPIIChecker()
        except Exception as e:
            logger.warning(f"Failed to load PII model, using fallback: {e}")
            from guardrails.types.pii_checker import PIIChecker
            self.guardrails[GuardrailType.PII] = PIIChecker()
    
    def _init_prompt_injection_checker(self, config):
        """Initialize prompt injection checker."""
        from guardrails.core.guardrail_config import GuardrailModelType
        model_type = config.get_model_for_type("prompt_injection")
        try:
            if model_type == GuardrailModelType.PROTECTAI_DEBERTA.value:
                from guardrails.types.protectai_prompt_injection_checker import ProtectAIPromptInjectionChecker
                self.guardrails[GuardrailType.PROMPT_INJECTION] = ProtectAIPromptInjectionChecker()
            else:
                from guardrails.types.enhanced_prompt_injection_checker import EnhancedPromptInjectionChecker
                self.guardrails[GuardrailType.PROMPT_INJECTION] = EnhancedPromptInjectionChecker()
        except Exception as e:
            logger.warning(f"Failed to load prompt injection model, using fallback: {e}")
            from guardrails.types.prompt_injection_checker import PromptInjectionChecker
            self.guardrails[GuardrailType.PROMPT_INJECTION] = PromptInjectionChecker()
    
    def _init_secret_scanner(self, config):
        """Initialize secret scanner."""
        try:
            from guardrails.types.secret_scanner import SecretScanner
            # Add as new guardrail type or use existing
            self.guardrails[GuardrailType.CUSTOM] = SecretScanner()
        except Exception as e:
            logger.warning(f"Failed to load secret scanner: {e}")
    
    def _init_policy_checker(self, config):
        """Initialize policy compliance checker."""
        try:
            from guardrails.types.policy_compliance_checker import PolicyComplianceChecker
            # Store separately or add to custom type
            if not hasattr(self, 'policy_checker'):
                self.policy_checker = PolicyComplianceChecker()
        except Exception as e:
            logger.warning(f"Failed to load policy checker: {e}")
    
    def _init_all_in_one_judge(self, config):
        """Initialize all-in-one safety judge (optional)."""
        if config.config.get("all_in_one_judge", {}).get("optional", False):
            try:
                from guardrails.types.llama_guard_checker import LlamaGuardChecker
                if not hasattr(self, 'all_in_one_judge'):
                    self.all_in_one_judge = LlamaGuardChecker()
            except Exception as e:
                logger.debug(f"All-in-one judge not available: {e}")
    
    def check_request(
        self,
        prompt: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        use_case: Optional[str] = None
    ) -> Tuple[bool, List[GuardrailResult]]:
        """
        Check a request (prompt) against all enabled guardrails.
        
        Args:
            prompt: User prompt to check
            user_id: Optional user identifier
            metadata: Optional metadata about the request
            use_case: Optional use case type (chat, rag, code_gen, batch)
            
        Returns:
            Tuple of (allowed, results) where:
            - allowed: True if request should be allowed
            - results: List of guardrail results
        """
        start_time = time.time()
        results = []
        allowed = True
        
        # Optimize model selection based on use case if latency budget manager available
        if self.latency_budget_manager and use_case:
            try:
                use_case_enum = UseCase(use_case)
                optimized_models = self.latency_budget_manager.get_optimized_models(use_case_enum)
                # Filter policies based on optimized models
                active_policies = [
                    p for p in self.policies
                    if p.enabled and optimized_models.get(p.guardrail_type.value) is not None
                ]
            except (ValueError, AttributeError):
                active_policies = [p for p in self.policies if p.enabled]
        else:
            active_policies = [p for p in self.policies if p.enabled]
        
        for policy in active_policies:
            # Check if this guardrail type should run on requests
            if not self.config.should_pre_filter(policy.guardrail_type.value):
                continue
            
            # All-in-one judge runs separately if available
            if policy.guardrail_type == GuardrailType.ALL_IN_ONE and self.all_in_one_judge:
                guardrail = self.all_in_one_judge
            else:
                guardrail = self.guardrails.get(policy.guardrail_type)
            
            if not guardrail:
                logger.warning(f"Guardrail {policy.guardrail_type} not available")
                continue
            
            try:
                start_time = time.time()
                result = guardrail.check(prompt, threshold=policy.threshold)
                duration = time.time() - start_time
                
                result.guardrail_type = policy.guardrail_type
                result.action = policy.action
                results.append(result)
                
                # Record metrics
                if self.metrics:
                    self.metrics.record_request_check(
                        guardrail_type=policy.guardrail_type.value,
                        passed=result.passed,
                        confidence=result.confidence,
                        duration=duration,
                        use_case=use_case
                    )
                    
                    # Check if budget exceeded
                    if use_case and self.latency_budget_manager:
                        try:
                            use_case_enum = UseCase(use_case)
                            budget_ms = self.latency_budget_manager.get_guardrail_budget_ms(use_case_enum)
                            if duration * 1000 > budget_ms:
                                self.metrics.latency_budget_exceeded.labels(use_case=use_case).inc()
                        except (ValueError, AttributeError):
                            pass
                
                if not result.passed:
                    logger.warning(
                        f"Guardrail {policy.guardrail_type.value} triggered: "
                        f"{result.message} (confidence: {result.confidence:.2f})"
                    )
                    
                    if policy.action == GuardrailAction.BLOCK:
                        allowed = False
                    elif policy.action == GuardrailAction.ALLOW_WITH_WARNING:
                        # Allow but mark for logging/watermarking
                        logger.warning(f"Soft fail for {policy.guardrail_type.value}: {result.message}")
                        # Could add watermark or weaken response here
                    elif policy.action == GuardrailAction.REDACT:
                        if result.redacted_content:
                            prompt = result.redacted_content
            except Exception as e:
                logger.error(f"Error checking guardrail {policy.guardrail_type}: {e}")
                # On error, allow the request but log it
                results.append(GuardrailResult(
                    passed=True,
                    guardrail_type=policy.guardrail_type,
                    action=policy.action,
                    confidence=0.0,
                    message=f"Error: {str(e)}"
                ))
        
        # Track total latency
        total_latency_ms = (time.time() - start_time) * 1000
        if self.latency_budget_manager and use_case:
            try:
                use_case_enum = UseCase(use_case)
                fits_budget, budget_msg = self.latency_budget_manager.validate_budget(
                    use_case_enum, int(total_latency_ms)
                )
                if not fits_budget:
                    logger.warning(f"Guardrail latency exceeds budget: {budget_msg}")
            except (ValueError, AttributeError):
                pass
        
        return allowed, results
    
    def check_response(
        self,
        response: str,
        original_prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[GuardrailResult]]:
        """
        Check a response against all enabled guardrails.
        
        Args:
            response: Model response to check
            original_prompt: Original prompt (for context)
            metadata: Optional metadata about the response
            
        Returns:
            Tuple of (allowed, results) where:
            - allowed: True if response should be allowed
            - results: List of guardrail results
        """
        results = []
        allowed = True
        
        for policy in self.policies:
            if not policy.enabled:
                continue
            
            # Check if this guardrail type should run on responses
            if not self.config.should_post_filter(policy.guardrail_type.value):
                continue
            
            # All-in-one judge runs separately if available
            if policy.guardrail_type == GuardrailType.ALL_IN_ONE and self.all_in_one_judge:
                guardrail = self.all_in_one_judge
            else:
                guardrail = self.guardrails.get(policy.guardrail_type)
            
            if not guardrail:
                continue
            
            guardrail = self.guardrails.get(policy.guardrail_type)
            if not guardrail:
                continue
            
            try:
                start_time = time.time()
                result = guardrail.check(response, threshold=policy.threshold)
                duration = time.time() - start_time
                
                result.guardrail_type = policy.guardrail_type
                result.action = policy.action
                results.append(result)
                
                # Record metrics
                if self.metrics:
                    self.metrics.record_response_check(
                        guardrail_type=policy.guardrail_type.value,
                        passed=result.passed,
                        confidence=result.confidence,
                        duration=duration
                    )
                
                if not result.passed:
                    logger.warning(
                        f"Guardrail {policy.guardrail_type.value} triggered in response: "
                        f"{result.message} (confidence: {result.confidence:.2f})"
                    )
                    
                    if policy.action == GuardrailAction.BLOCK:
                        allowed = False
            except Exception as e:
                logger.error(f"Error checking guardrail {policy.guardrail_type}: {e}")
                results.append(GuardrailResult(
                    passed=True,
                    guardrail_type=policy.guardrail_type,
                    action=policy.action,
                    confidence=0.0,
                    message=f"Error: {str(e)}"
                ))
        
        return allowed, results
    
    def update_policy(
        self,
        guardrail_type: GuardrailType,
        enabled: Optional[bool] = None,
        action: Optional[GuardrailAction] = None,
        threshold: Optional[float] = None
    ) -> bool:
        """
        Update a guardrail policy.
        
        Args:
            guardrail_type: Type of guardrail to update
            enabled: Whether to enable/disable
            action: Action to take when triggered
            threshold: Confidence threshold
            
        Returns:
            True if policy was updated
        """
        for policy in self.policies:
            if policy.guardrail_type == guardrail_type:
                if enabled is not None:
                    policy.enabled = enabled
                if action is not None:
                    policy.action = action
                if threshold is not None:
                    policy.threshold = threshold
                logger.info(f"Updated policy for {guardrail_type.value}")
                return True
        
        logger.warning(f"Policy for {guardrail_type.value} not found")
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all guardrails."""
        return {
            "policies": [
                {
                    "type": policy.guardrail_type.value,
                    "enabled": policy.enabled,
                    "action": policy.action.value,
                    "threshold": policy.threshold
                }
                for policy in self.policies
            ],
            "available_guardrails": list(self.guardrails.keys())
        }

