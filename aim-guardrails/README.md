# AIM Guardrails Microservice

Production-ready safety and filtering layers for AI inference endpoints. Provides comprehensive guardrails including toxicity detection, PII detection, and prompt injection protection.

## Overview

The AIM Guardrails Microservice provides a unified interface for applying multiple safety checks to AI inference requests and responses. It can be deployed as a sidecar, proxy, or standalone service alongside inference endpoints.

## Features

- **Comprehensive Guardrail Types** (Production-Ready):
  - **Safety/Toxicity** - RoBERTa toxicity classifier, Detoxify, XLM-RoBERTa (multilingual)
  - **PII Detection** - Piiranha (multilingual), Presidio, ab-ai/pii_model, Phi-3 Mini
  - **Prompt Injection** - ProtectAI DeBERTa-v3, enhanced pattern matching
  - **All-in-One Judge** - Llama Guard 2/3 for comprehensive safety classification
  - **Policy/Compliance** - LLM-as-judge (Qwen2.5-3B, Phi-3, Llama-3.2-3B) for enterprise policies
  - **Secrets/IP/Code Safety** - Pattern-based secret scanner (Gitleaks-style)
  - **Traffic Guardrails** - Rate limiting, quotas, geo restrictions, business hours
- **Flexible Configuration** - YAML-based model selection with pre/post filter support
- **Automatic Fallback** - Graceful degradation if ML models unavailable
  
- **Flexible Actions**:
  - Block - Prevent request/response from proceeding
  - Warn - Allow but log warning
  - Redact - Remove sensitive content
  - Modify - Modify content before proceeding

- **Kubernetes Native**:
  - GuardrailPolicy CRD
  - Kubernetes deployment manifests with proper resource limits
  - ConfigMap-based policy configuration
  - ServiceMonitor for Prometheus integration
- **Production Monitoring**:
  - Prometheus metrics export
  - Request/response metrics tracking
  - Performance monitoring
  - Model availability tracking

- **Integration Ready**:
  - REST API for guardrail checking
  - Inference proxy for automatic integration
  - Sidecar deployment pattern

## Quick Start

### Installation

```bash
cd aim-guardrails
pip install -r requirements.txt --break-system-packages
```

**Note**: ML models will be downloaded automatically on first use. Total size ~2-3GB depending on which models you use:
- RoBERTa toxicity: ~500MB
- Piiranha PII: ~500MB
- ProtectAI DeBERTa: ~500MB
- Llama Guard 3-8B: ~16GB (or 1B: ~2GB)
- Presidio: ~200MB
- Sentence transformers: ~100MB

For production, consider pre-downloading models in your Docker image.

### Configuration

Configure which models to use in `guardrails/core/guardrail_config.yaml`:

```yaml
guardrails:
  toxicity:
    model: roberta_toxicity  # or detoxify, xlm_toxicity
  pii:
    model: piiranha  # or presidio, ab_ai_pii, phi3_pii
  prompt_injection:
    model: protectai_deberta  # or enhanced_pattern
  all_in_one_judge:
    model: llama_guard
    model_name: "meta-llama/LlamaGuard-3-8B"
```

See [GUARDRAIL_MODELS.md](./GUARDRAIL_MODELS.md) for complete model reference.

### Basic Usage

```python
from guardrails.core.guardrail_service import GuardrailService

# Initialize service with default policies
service = GuardrailService()

# Check a request
allowed, results = service.check_request("What is AI?")
if allowed:
    print("Request is safe")
else:
    print("Request blocked by guardrails")

# Check a response
allowed, results = service.check_response("Model response text")
```

### API Server

Start the REST API server:

```bash
# With default configuration
python3 -m guardrails.api.server

# With custom configuration
GUARDRAIL_CONFIG_YAML=./guardrails/core/guardrail_config.yaml \
ENABLE_METRICS=true \
python3 -m guardrails.api.server
```

The server will run on port 8080 (API) and 9090 (metrics, if enabled).

### API Endpoints

- `GET /health` - Health check
- `GET /status` - Get guardrail service status
- `POST /check/request` - Check a request (prompt)
- `POST /check/response` - Check a response
- `GET /policy` - Get all policies
- `PUT /policy/<type>` - Update a policy

### Example API Usage

```bash
# Check a request
curl -X POST http://localhost:8080/check/request \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is AI?"}'

# Check a response
curl -X POST http://localhost:8080/check/response \
  -H "Content-Type: application/json" \
  -d '{"response": "Model response text"}'
```

## Guardrail Types

### ML-Based Toxicity Detection

Uses **Detoxify** ML model for accurate toxicity detection. Detects multiple toxicity categories:
- Toxicity
- Severe toxicity
- Obscene
- Threat
- Insult
- Identity attack

**Model**: Detoxify (pre-trained on Jigsaw dataset)
**Fallback**: Pattern-based detection if model unavailable

```python
from guardrails.core.guardrail_service import GuardrailService, GuardrailPolicy, GuardrailType, GuardrailAction

policies = [
    GuardrailPolicy(
        guardrail_type=GuardrailType.TOXICITY,
        enabled=True,
        action=GuardrailAction.BLOCK,
        threshold=0.7
    )
]
service = GuardrailService(policies=policies)
```

### ML-Based PII Detection

Uses **Presidio** (Microsoft) for comprehensive PII detection and redaction:
- Person names
- Email addresses
- Phone numbers
- Social Security Numbers
- Credit card numbers
- IP addresses
- Dates
- Locations
- Organizations
- And more (20+ entity types)

**Model**: Presidio Analyzer (spaCy NER + custom models)
**Fallback**: Regex-based detection if model unavailable

```python
policies = [
    GuardrailPolicy(
        guardrail_type=GuardrailType.PII,
        enabled=True,
        action=GuardrailAction.REDACT,
        threshold=0.8
    )
]
```

### Enhanced Prompt Injection Detection

Combines pattern matching with semantic similarity for robust detection:
- Pattern-based detection (common injection phrases)
- Semantic similarity (compares against known injection patterns)
- Heuristic analysis (unusual patterns, mixed case, etc.)

**Model**: Sentence transformers (all-MiniLM-L6-v2) for semantic similarity
**Fallback**: Pattern-based detection if model unavailable

```python
policies = [
    GuardrailPolicy(
        guardrail_type=GuardrailType.PROMPT_INJECTION,
        enabled=True,
        action=GuardrailAction.BLOCK,
        threshold=0.75
    )
]
```

## Policy Configuration

### Using Policy Manager

```python
from guardrails.policy.policy_manager import PolicyManager

# Load from file
policy_manager = PolicyManager(config_path="policy.json")

# Or use defaults
policy_manager = PolicyManager()

policies = policy_manager.get_policies()
service = GuardrailService(policies=policies)
```

### Policy JSON Format

```json
{
  "policies": [
    {
      "type": "toxicity",
      "enabled": true,
      "action": "block",
      "threshold": 0.7
    },
    {
      "type": "pii",
      "enabled": true,
      "action": "redact",
      "threshold": 0.8
    },
    {
      "type": "prompt_injection",
      "enabled": true,
      "action": "block",
      "threshold": 0.75
    }
  ]
}
```

## Integration with Inference Endpoints

### Using Inference Proxy

```python
from guardrails.integration.inference_proxy import InferenceProxy
from guardrails.core.guardrail_service import GuardrailService

service = GuardrailService()
proxy = InferenceProxy(
    inference_endpoint="http://inference-service:8000/predict",
    guardrail_service=service
)

# Forward request through guardrails
allowed, response, error = proxy.forward_request(
    prompt="What is AI?",
    user_id="user123"
)

if allowed:
    print(f"Response: {response}")
else:
    print(f"Error: {error}")
```

## Kubernetes Deployment

### Deploy Guardrail Service

```bash
# Create namespace
kubectl create namespace aim-guardrails

# Deploy CRD
kubectl apply -f k8s/crd/guardrail-policy-crd.yaml

# Deploy service
kubectl apply -f k8s/deployment/guardrail-deployment.yaml

# Deploy ServiceMonitor for Prometheus (optional)
kubectl apply -f k8s/monitoring/service-monitor.yaml
```

### Resource Requirements

The deployment includes proper resource limits for ML models:
- **Requests**: 1Gi memory, 500m CPU
- **Limits**: 2Gi memory, 2000m CPU

Models are loaded on startup, so initial memory usage is higher.

### Monitoring

Metrics are exposed on port 9090:
- `guardrail_requests_total` - Total request checks
- `guardrail_requests_blocked_total` - Blocked requests
- `guardrail_check_duration_seconds` - Check latency
- `guardrail_confidence_score` - Detection confidence
- `guardrail_model_available` - Model availability status

### Create GuardrailPolicy

```yaml
apiVersion: aim.amd.com/v1alpha1
kind: GuardrailPolicy
metadata:
  name: default-guardrails
  namespace: aim-guardrails
spec:
  guardrails:
    - type: toxicity
      enabled: true
      action: block
      threshold: 0.7
    - type: pii
      enabled: true
      action: redact
      threshold: 0.8
    - type: prompt_injection
      enabled: true
      action: block
      threshold: 0.75
  mode: sidecar
```

## Testing

Run the test script:

```bash
chmod +x test_guardrails.sh
./test_guardrails.sh
```

Or test manually:

```python
python3 examples/example_usage.py
```

## Architecture

```
aim-guardrails/
├── guardrails/          # Core guardrail components
│   ├── core/           # Guardrail service
│   ├── types/          # Guardrail type implementations
│   ├── policy/         # Policy management
│   └── api/            # REST API server
├── integration/        # Inference endpoint integration
├── k8s/                # Kubernetes resources
│   ├── crd/            # Custom Resource Definitions
│   └── deployment/     # Deployment manifests
├── examples/           # Usage examples
└── tests/              # Test scripts
```

## Development Status

✅ **Core Guardrail Service** - Complete
- [x] Guardrail service with multiple types
- [x] Toxicity detection
- [x] PII detection and redaction
- [x] Prompt injection detection
- [x] Policy management

✅ **API Server** - Complete
- [x] REST API endpoints
- [x] Request/response checking
- [x] Policy management API

✅ **Kubernetes Integration** - Complete
- [x] GuardrailPolicy CRD
- [x] Deployment manifests
- [x] ConfigMap-based configuration

✅ **Integration** - Complete
- [x] Inference proxy
- [x] Sidecar deployment pattern

## Configuration

### Environment Variables

- `PORT` - API server port (default: 8080)
- `GUARDRAIL_CONFIG` - Path to policy configuration file

### Policy Actions

- `block` - Block the request/response
- `warn` - Allow but log warning
- `redact` - Remove sensitive content
- `modify` - Modify content before proceeding

## Examples

See `examples/example_usage.py` for comprehensive usage examples.

## Troubleshooting

- **Import errors**: Ensure all dependencies are installed from `requirements.txt`
- **API not responding**: Check if server is running and port is accessible
- **Policies not loading**: Verify policy JSON format is correct
- **Guardrails not triggering**: Check threshold values and enabled status

## License

MIT License
