"""
Latency budget management for different AIM use cases.

Defines latency budgets and optimizes guardrail selection based on use case.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class UseCase(Enum):
    """AIM use case types."""
    CHAT = "chat"  # Chat/assistant (no tools)
    RAG = "rag"  # RAG / internal Q&A
    CODE_GEN = "code_gen"  # Code generation / refactor
    BATCH = "batch"  # Batch summarize / offline jobs


@dataclass
class LatencyBudget:
    """Latency budget for a use case."""
    use_case: UseCase
    p50_e2e_ms: int  # 50th percentile end-to-end latency
    p95_e2e_ms: int  # 95th percentile end-to-end latency
    guardrail_budget_ms: int  # Budget for guardrail checks
    notes: str = ""


class LatencyBudgetManager:
    """Manages latency budgets for different use cases."""
    
    # Latency budgets based on user requirements
    BUDGETS = {
        UseCase.CHAT: LatencyBudget(
            use_case=UseCase.CHAT,
            p50_e2e_ms=900,
            p95_e2e_ms=1500,
            guardrail_budget_ms=100,  # ~10% of E2E budget
            notes="200-400 in/out tokens, interactive UX"
        ),
        UseCase.RAG: LatencyBudget(
            use_case=UseCase.RAG,
            p50_e2e_ms=1200,
            p95_e2e_ms=1800,
            guardrail_budget_ms=150,  # ~12% of E2E budget
            notes="Adds retrieval + hallucination check"
        ),
        UseCase.CODE_GEN: LatencyBudget(
            use_case=UseCase.CODE_GEN,
            p50_e2e_ms=1400,
            p95_e2e_ms=2000,
            guardrail_budget_ms=200,  # ~14% of E2E budget
            notes="Longer responses, plus IP/secrets scan"
        ),
        UseCase.BATCH: LatencyBudget(
            use_case=UseCase.BATCH,
            p50_e2e_ms=0,  # Not latency-sensitive
            p95_e2e_ms=0,
            guardrail_budget_ms=500,  # Throughput optimized
            notes="Throughput optimized, not latency-sensitive"
        ),
    }
    
    def __init__(self):
        """Initialize latency budget manager."""
        self.budgets = self.BUDGETS.copy()
        logger.info("Latency budget manager initialized")
    
    def get_budget(self, use_case: UseCase) -> LatencyBudget:
        """Get latency budget for a use case."""
        return self.budgets.get(use_case, self.budgets[UseCase.CHAT])
    
    def get_guardrail_budget_ms(self, use_case: UseCase) -> int:
        """Get guardrail latency budget in milliseconds."""
        return self.get_budget(use_case).guardrail_budget_ms
    
    def get_optimized_models(self, use_case: UseCase) -> Dict[str, str]:
        """
        Get optimized model selection for use case based on latency budget.
        
        Returns:
            Dictionary mapping guardrail type to model name
        """
        budget_ms = self.get_guardrail_budget_ms(use_case)
        
        # Model latency estimates (ms)
        # Small models (CPU): 10-50ms
        # Medium models (CPU/GPU): 50-200ms
        # Large models (GPU): 200-1000ms
        
        if use_case == UseCase.CHAT:
            # Tight budget: use fastest models
            return {
                "toxicity": "roberta_toxicity",  # ~20ms
                "pii": "presidio",  # ~50ms (faster than piiranha)
                "prompt_injection": "protectai_deberta",  # ~30ms
                "all_in_one_judge": None,  # Skip (too slow for chat)
                "policy_compliance": None,  # Skip (post-filter only)
                "secrets": "secret_scanner",  # ~5ms
            }
        elif use_case == UseCase.RAG:
            # Medium budget: can use slightly slower models
            return {
                "toxicity": "roberta_toxicity",  # ~20ms
                "pii": "piiranha",  # ~100ms (more accurate)
                "prompt_injection": "protectai_deberta",  # ~30ms
                "all_in_one_judge": "llama_guard",  # ~300ms (post-filter)
                "policy_compliance": None,  # Optional
                "secrets": "secret_scanner",  # ~5ms
            }
        elif use_case == UseCase.CODE_GEN:
            # Larger budget: can use more comprehensive checks
            return {
                "toxicity": "roberta_toxicity",  # ~20ms
                "pii": "piiranha",  # ~100ms
                "prompt_injection": "protectai_deberta",  # ~30ms
                "all_in_one_judge": "llama_guard",  # ~300ms (post-filter)
                "policy_compliance": "policy_llm",  # ~500ms (post-filter)
                "secrets": "secret_scanner",  # ~5ms (critical for code)
            }
        else:  # BATCH
            # Throughput optimized: can use all models
            return {
                "toxicity": "roberta_toxicity",
                "pii": "piiranha",
                "prompt_injection": "protectai_deberta",
                "all_in_one_judge": "llama_guard",
                "policy_compliance": "policy_llm",
                "secrets": "secret_scanner",
            }
    
    def estimate_total_latency(self, use_case: UseCase, models: Dict[str, str]) -> int:
        """
        Estimate total guardrail latency for given models.
        
        Args:
            use_case: Use case type
            models: Dictionary of guardrail type -> model name
            
        Returns:
            Estimated total latency in milliseconds
        """
        # Model latency estimates (ms)
        latency_map = {
            "roberta_toxicity": 20,
            "detoxify": 100,
            "xlm_toxicity": 150,
            "presidio": 50,
            "piiranha": 100,
            "ab_ai_pii": 80,
            "phi3_pii": 200,
            "protectai_deberta": 30,
            "enhanced_pattern": 10,
            "llama_guard": 300,
            "policy_llm": 500,
            "secret_scanner": 5,
        }
        
        total = 0
        for guardrail_type, model_name in models.items():
            if model_name:
                latency = latency_map.get(model_name, 100)  # Default 100ms
                total += latency
        
        return total
    
    def validate_budget(self, use_case: UseCase, estimated_latency_ms: int) -> Tuple[bool, str]:
        """
        Validate if estimated latency fits within budget.
        
        Returns:
            Tuple of (fits_budget, message)
        """
        budget = self.get_guardrail_budget_ms(use_case)
        fits = estimated_latency_ms <= budget
        
        if use_case == UseCase.BATCH:
            message = f"Batch mode: {estimated_latency_ms}ms (throughput optimized)"
        else:
            message = f"{'✓' if fits else '✗'} {estimated_latency_ms}ms / {budget}ms budget"
        
        return fits, message

