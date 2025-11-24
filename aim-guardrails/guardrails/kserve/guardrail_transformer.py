"""
KServe Transformer for guardrail service.

Implements KServe V2 protocol for guardrail integration.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from guardrails.core.guardrail_service import GuardrailService
from guardrails.core.latency_budget import UseCase, LatencyBudgetManager

logger = logging.getLogger(__name__)


class GuardrailTransformer:
    """KServe transformer for guardrail service."""
    
    def __init__(self, guardrail_service: GuardrailService):
        """
        Initialize guardrail transformer.
        
        Args:
            guardrail_service: Guardrail service instance
        """
        self.guardrail_service = guardrail_service
        self.latency_budget_manager = LatencyBudgetManager()
        logger.info("Guardrail transformer initialized")
    
    def preprocess(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess request (pre-filter guardrails).
        
        Args:
            inputs: KServe V2 request inputs
            
        Returns:
            Preprocessed inputs (or error if blocked)
        """
        try:
            # Extract prompt from KServe request
            instances = inputs.get("instances", [])
            if not instances:
                return {"error": "No instances in request"}
            
            # Get first instance (assuming single prompt per request)
            instance = instances[0]
            prompt = instance.get("prompt") or instance.get("text") or instance.get("input")
            
            if not prompt:
                return {"error": "No prompt found in request"}
            
            # Determine use case from metadata
            use_case = instance.get("use_case", "chat")
            user_id = instance.get("user_id")
            metadata = instance.get("metadata", {})
            
            # Check guardrails
            allowed, results = self.guardrail_service.check_request(
                prompt=prompt,
                user_id=user_id,
                metadata=metadata,
                use_case=use_case
            )
            
            if not allowed:
                # Block request
                blocked_reasons = [r.message for r in results if not r.passed]
                return {
                    "error": "Request blocked by guardrails",
                    "reasons": blocked_reasons,
                    "results": [
                        {
                            "type": r.guardrail_type.value if r.guardrail_type else None,
                            "message": r.message,
                            "confidence": r.confidence
                        }
                        for r in results if not r.passed
                    ]
                }
            
            # Apply redactions if any
            redacted_prompt = prompt
            for result in results:
                if result.redacted_content:
                    redacted_prompt = result.redacted_content
            
            # Return preprocessed input
            instance["prompt"] = redacted_prompt
            instance["original_prompt"] = prompt  # Keep original for reference
            instance["guardrail_metadata"] = {
                "pre_filter_passed": True,
                "results": [
                    {
                        "type": r.guardrail_type.value if r.guardrail_type else None,
                        "passed": r.passed,
                        "confidence": r.confidence
                    }
                    for r in results
                ]
            }
            
            return {"instances": [instance]}
            
        except Exception as e:
            logger.error(f"Error in preprocessing: {e}")
            return {"error": str(e)}
    
    def postprocess(self, inputs: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Postprocess response (post-filter guardrails).
        
        Args:
            inputs: Original request inputs
            response: AIM model response
            
        Returns:
            Postprocessed response (or error if blocked)
        """
        try:
            # Extract response from AIM output
            outputs = response.get("outputs", [])
            if not outputs:
                return response
            
            # Get first output
            output = outputs[0]
            model_response = output.get("data") or output.get("text") or output.get("content")
            
            if not model_response:
                return response
            
            # Get original prompt and use case
            instances = inputs.get("instances", [])
            original_prompt = None
            use_case = "chat"
            
            if instances:
                instance = instances[0]
                original_prompt = instance.get("original_prompt") or instance.get("prompt")
                use_case = instance.get("use_case", "chat")
            
            # Check guardrails on response
            allowed, results = self.guardrail_service.check_response(
                response=model_response,
                original_prompt=original_prompt,
                metadata={"use_case": use_case}
            )
            
            if not allowed:
                # Block response
                blocked_reasons = [r.message for r in results if not r.passed]
                return {
                    "error": "Response blocked by guardrails",
                    "reasons": blocked_reasons,
                    "results": [
                        {
                            "type": r.guardrail_type.value if r.guardrail_type else None,
                            "message": r.message,
                            "confidence": r.confidence
                        }
                        for r in results if not r.passed
                    ]
                }
            
            # Apply redactions if any
            redacted_response = model_response
            for result in results:
                if result.redacted_content:
                    redacted_response = result.redacted_content
            
            # Update response
            output["data"] = redacted_response
            output["guardrail_metadata"] = {
                "post_filter_passed": True,
                "redacted": redacted_response != model_response,
                "results": [
                    {
                        "type": r.guardrail_type.value if r.guardrail_type else None,
                        "passed": r.passed,
                        "confidence": r.confidence
                    }
                    for r in results
                ]
            }
            
            return {"outputs": [output]}
            
        except Exception as e:
            logger.error(f"Error in postprocessing: {e}")
            return response  # Return original response on error

