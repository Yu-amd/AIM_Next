"""
REST API server for guardrail service.

Provides HTTP endpoints for guardrail checking with traffic-level guardrails.
"""

import logging
from flask import Flask, request, jsonify
from typing import Dict, Any, Optional
from guardrails.core.guardrail_service import GuardrailService, GuardrailPolicy, GuardrailType, GuardrailAction
from guardrails.policy.policy_manager import PolicyManager
from guardrails.core.guardrail_config import GuardrailConfig
from guardrails.traffic.rate_limiter import RateLimiter, RateLimitConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global guardrail service instance
guardrail_service: Optional[GuardrailService] = None
rate_limiter: Optional[RateLimiter] = None


def init_service(config_path: Optional[str] = None, enable_metrics: bool = False, guardrail_config_path: Optional[str] = None):
    """Initialize guardrail service."""
    global guardrail_service, rate_limiter
    
    import os
    import yaml
    
    enable_metrics = os.environ.get('ENABLE_METRICS', 'false').lower() == 'true' or enable_metrics
    
    # Load guardrail configuration
    guardrail_config = None
    if guardrail_config_path:
        try:
            with open(guardrail_config_path, 'r') as f:
                config_dict = yaml.safe_load(f)
                guardrail_config = GuardrailConfig(config_dict.get('guardrails', {}))
        except Exception as e:
            logger.warning(f"Failed to load guardrail config: {e}")
    
    # Initialize rate limiter
    if guardrail_config_path:
        try:
            with open(guardrail_config_path, 'r') as f:
                config_dict = yaml.safe_load(f)
                traffic_config = config_dict.get('traffic', {})
                rate_limit_config = RateLimitConfig(
                    requests_per_minute=traffic_config.get('rate_limits', {}).get('requests_per_minute', 60),
                    requests_per_hour=traffic_config.get('rate_limits', {}).get('requests_per_hour', 1000),
                    requests_per_day=traffic_config.get('rate_limits', {}).get('requests_per_day', 10000),
                    max_context_length=traffic_config.get('context_limits', {}).get('max_context_length', 8192),
                    max_upload_size_mb=traffic_config.get('context_limits', {}).get('max_upload_size_mb', 10),
                    allowed_geos=traffic_config.get('access_control', {}).get('allowed_geos'),
                    business_hours_only=traffic_config.get('access_control', {}).get('business_hours_only', False),
                    business_hours_start=traffic_config.get('access_control', {}).get('business_hours_start', 9),
                    business_hours_end=traffic_config.get('access_control', {}).get('business_hours_end', 17)
                )
                rate_limiter = RateLimiter(rate_limit_config)
        except Exception as e:
            logger.warning(f"Failed to load rate limiter config: {e}")
            rate_limiter = RateLimiter()
    else:
        rate_limiter = RateLimiter()
    
    policy_manager = PolicyManager(config_path=config_path)
    guardrail_service = GuardrailService(
        policies=policy_manager.get_policies(),
        enable_metrics=enable_metrics,
        config=guardrail_config
    )
    
    logger.info(f"Guardrail service initialized (metrics: {enable_metrics})")


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "aim-guardrails"}), 200


@app.route('/status', methods=['GET'])
def status():
    """Get guardrail service status."""
    if not guardrail_service:
        return jsonify({"error": "Service not initialized"}), 500
    
    status_data = guardrail_service.get_status()
    
    # Add rate limiter status
    if rate_limiter:
        status_data["rate_limiter"] = {
            "enabled": True,
            "config": {
                "requests_per_minute": rate_limiter.config.requests_per_minute,
                "requests_per_hour": rate_limiter.config.requests_per_hour,
                "requests_per_day": rate_limiter.config.requests_per_day,
                "max_context_length": rate_limiter.config.max_context_length,
                "max_upload_size_mb": rate_limiter.config.max_upload_size_mb
            }
        }
    else:
        status_data["rate_limiter"] = {"enabled": False}
    
    return jsonify(status_data), 200


@app.route('/check/request', methods=['POST'])
def check_request():
    """
    Check a request (prompt) against guardrails.
    
    Request body:
    {
        "prompt": "user prompt text",
        "user_id": "optional user id",
        "api_key": "optional api key",
        "context_length": 0,
        "upload_size_mb": 0.0,
        "geo": "optional geographic location",
        "metadata": {}
    }
    """
    if not guardrail_service:
        return jsonify({"error": "Service not initialized"}), 500
    
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        user_id = data.get('user_id')
        api_key = data.get('api_key')
        context_length = data.get('context_length', 0)
        upload_size_mb = data.get('upload_size_mb', 0.0)
        geo = data.get('geo')
        use_case = data.get('use_case', 'chat')  # chat, rag, code_gen, batch
        metadata = data.get('metadata', {})
        
        if not prompt:
            return jsonify({"error": "prompt is required"}), 400
        
        # Check rate limits first
        if rate_limiter:
            allowed, rate_limit_msg = rate_limiter.check_rate_limit(
                user_id=user_id or "anonymous",
                api_key=api_key,
                context_length=context_length,
                upload_size_mb=upload_size_mb,
                geo=geo
            )
            if not allowed:
                return jsonify({
                    "allowed": False,
                    "error": "rate_limit",
                    "message": rate_limit_msg
                }), 429
        
        # Check guardrails
        allowed, results = guardrail_service.check_request(
            prompt=prompt,
            user_id=user_id,
            metadata=metadata,
            use_case=use_case
        )
        
        return jsonify({
            "allowed": allowed,
            "results": [
                {
                    "type": r.guardrail_type.value if r.guardrail_type else None,
                    "passed": r.passed,
                    "action": r.action.value if r.action else None,
                    "confidence": r.confidence,
                    "message": r.message,
                    "details": r.details
                }
                for r in results
            ]
        }), 200 if allowed else 403
        
    except Exception as e:
        logger.error(f"Error checking request: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/check/response', methods=['POST'])
def check_response():
    """
    Check a response against guardrails.
    
    Request body:
    {
        "response": "model response text",
        "original_prompt": "original prompt",
        "metadata": {}
    }
    """
    if not guardrail_service:
        return jsonify({"error": "Service not initialized"}), 500
    
    try:
        data = request.get_json()
        response = data.get('response', '')
        original_prompt = data.get('original_prompt')
        metadata = data.get('metadata', {})
        
        if not response:
            return jsonify({"error": "response is required"}), 400
        
        allowed, results = guardrail_service.check_response(
            response=response,
            original_prompt=original_prompt,
            metadata=metadata
        )
        
        return jsonify({
            "allowed": allowed,
            "results": [
                {
                    "type": r.guardrail_type.value if r.guardrail_type else None,
                    "passed": r.passed,
                    "action": r.action.value if r.action else None,
                    "confidence": r.confidence,
                    "message": r.message,
                    "details": r.details,
                    "redacted_content": r.redacted_content
                }
                for r in results
            ]
        }), 200 if allowed else 403
        
    except Exception as e:
        logger.error(f"Error checking response: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/policy', methods=['GET'])
def get_policies():
    """Get all guardrail policies."""
    if not guardrail_service:
        return jsonify({"error": "Service not initialized"}), 500
    
    policies = guardrail_service.policies
    return jsonify({
        "policies": [
            {
                "type": p.guardrail_type.value,
                "enabled": p.enabled,
                "action": p.action.value,
                "threshold": p.threshold
            }
            for p in policies
        ]
    }), 200


@app.route('/policy/<guardrail_type>', methods=['PUT'])
def update_policy(guardrail_type: str):
    """
    Update a guardrail policy.
    
    Request body:
    {
        "enabled": true/false,
        "action": "allow|block|allow_with_warning|redact|modify",
        "threshold": 0.0-1.0
    }
    """
    if not guardrail_service:
        return jsonify({"error": "Service not initialized"}), 500
    
    try:
        data = request.get_json() or {}
        gr_type = GuardrailType(guardrail_type)
        
        enabled = data.get('enabled')
        action = data.get('action')
        threshold = data.get('threshold')
        
        if action:
            action = GuardrailAction(action)
        
        success = guardrail_service.update_policy(
            guardrail_type=gr_type,
            enabled=enabled,
            action=action,
            threshold=threshold
        )
        
        if success:
            return jsonify({"message": f"Policy {guardrail_type} updated"}), 200
        else:
            return jsonify({"error": f"Policy {guardrail_type} not found"}), 404
            
    except ValueError as e:
        return jsonify({"error": f"Invalid guardrail type or action: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Error updating policy: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/rate-limit/stats/<identifier>', methods=['GET'])
def get_rate_limit_stats(identifier: str):
    """Get rate limit statistics for a user/API key."""
    if not rate_limiter:
        return jsonify({"error": "Rate limiter not initialized"}), 500
    
    stats = rate_limiter.get_stats(identifier)
    return jsonify(stats), 200


if __name__ == '__main__':
    import os
    config_path = os.environ.get('GUARDRAIL_CONFIG', None)
    guardrail_config_path = os.environ.get('GUARDRAIL_CONFIG_YAML', None)
    enable_metrics = os.environ.get('ENABLE_METRICS', 'false').lower() == 'true'
    init_service(config_path=config_path, enable_metrics=enable_metrics, guardrail_config_path=guardrail_config_path)
    
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
