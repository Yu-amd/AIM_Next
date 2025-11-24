"""
Proxy for integrating guardrails with inference endpoints.

Intercepts requests/responses and applies guardrails before forwarding.
"""

import logging
import requests
from typing import Dict, Any, Optional, Tuple
from guardrails.core.guardrail_service import GuardrailService

logger = logging.getLogger(__name__)


class InferenceProxy:
    """Proxy that adds guardrails to inference endpoints."""
    
    def __init__(
        self,
        inference_endpoint: str,
        guardrail_service: GuardrailService
    ):
        """
        Initialize inference proxy.
        
        Args:
            inference_endpoint: URL of the inference endpoint
            guardrail_service: Guardrail service instance
        """
        self.inference_endpoint = inference_endpoint
        self.guardrail_service = guardrail_service
        
        logger.info(f"Inference proxy initialized for endpoint: {inference_endpoint}")
    
    def forward_request(
        self,
        prompt: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Forward a request through guardrails to inference endpoint.
        
        Args:
            prompt: User prompt
            user_id: Optional user identifier
            metadata: Optional metadata
            **kwargs: Additional parameters for inference endpoint
            
        Returns:
            Tuple of (allowed, response_data, error_message)
        """
        # Check request against guardrails
        allowed, results = self.guardrail_service.check_request(
            prompt=prompt,
            user_id=user_id,
            metadata=metadata
        )
        
        if not allowed:
            error_msg = f"Request blocked by guardrails: {[r.message for r in results if not r.passed]}"
            logger.warning(error_msg)
            return False, None, error_msg
        
        # Forward to inference endpoint
        try:
            payload = {
                "prompt": prompt,
                **kwargs
            }
            
            response = requests.post(
                self.inference_endpoint,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            response_data = response.json()
            model_response = response_data.get('response', '') or response_data.get('text', '')
            
            # Check response against guardrails
            if model_response:
                allowed, response_results = self.guardrail_service.check_response(
                    response=model_response,
                    original_prompt=prompt,
                    metadata=metadata
                )
                
                if not allowed:
                    error_msg = f"Response blocked by guardrails: {[r.message for r in response_results if not r.passed]}"
                    logger.warning(error_msg)
                    return False, None, error_msg
                
                # Apply redaction if needed
                for result in response_results:
                    if result.redacted_content:
                        response_data['response'] = result.redacted_content
                        response_data['redacted'] = True
            
            return True, response_data, None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error forwarding request to inference endpoint: {e}")
            return False, None, f"Inference endpoint error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False, None, f"Error: {str(e)}"
    
    def check_prompt_only(self, prompt: str, user_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Check a prompt without forwarding to inference endpoint.
        
        Args:
            prompt: User prompt
            user_id: Optional user identifier
            
        Returns:
            Tuple of (allowed, message)
        """
        allowed, results = self.guardrail_service.check_request(
            prompt=prompt,
            user_id=user_id
        )
        
        if not allowed:
            message = f"Prompt blocked: {[r.message for r in results if not r.passed]}"
            return False, message
        
        return True, "Prompt allowed"

