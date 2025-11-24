# KServe Integration Guide

Complete guide for integrating guardrails with AIM using KServe/Kubernetes architecture.

## Architecture Overview

```
User Request
    ↓
KServe Transformer (Guardrails Pre-Filter)
    ↓
AIM Inference Service (Predictor)
    ↓
KServe Transformer (Guardrails Post-Filter)
    ↓
User Response
```

## Latency Budgets

Based on AMD Instinct GPU (MI300X) performance:

| Use Case | p50 E2E | p95 E2E | Guardrail Budget | Notes |
|----------|---------|---------|------------------|-------|
| Chat/Assistant | ~900ms | ~1.5s | ~100ms | 200-400 tokens, interactive UX |
| RAG/Q&A | ~1.2s | ~1.8s | ~150ms | Adds retrieval + hallucination check |
| Code Generation | ~1.4s | ~2.0s | ~200ms | Longer responses + IP/secrets scan |
| Batch/Offline | N/A | N/A | ~500ms | Throughput optimized |

## Model Selection by Use Case

### Chat/Assistant (Tight Budget: ~100ms)

**Pre-Filters**:
- Prompt Injection: ProtectAI DeBERTa (~30ms)
- Toxicity: RoBERTa (~20ms)
- PII: Presidio (~50ms) - faster than Piiranha
- Secrets: Pattern scanner (~5ms)

**Post-Filters**:
- PII Redaction: Presidio (~50ms)
- (Skip all-in-one judge - too slow for chat)

**Total**: ~175ms (within budget with margin)

### RAG/Q&A (Medium Budget: ~150ms)

**Pre-Filters**:
- Prompt Injection: ProtectAI DeBERTa (~30ms)
- Toxicity: RoBERTa (~20ms)
- PII: Piiranha (~100ms) - more accurate
- Secrets: Pattern scanner (~5ms)

**Post-Filters**:
- All-in-One Judge: Llama Guard 3-1B (~300ms) - can run async
- PII Redaction: Piiranha (~100ms)

**Total**: ~255ms (can run some post-filters async)

### Code Generation (Larger Budget: ~200ms)

**Pre-Filters**:
- Prompt Injection: ProtectAI DeBERTa (~30ms)
- Toxicity: RoBERTa (~20ms)
- PII: Piiranha (~100ms)
- Secrets: Pattern scanner (~5ms) - critical for code

**Post-Filters**:
- All-in-One Judge: Llama Guard 3-8B (~500ms)
- PII Redaction: Piiranha (~100ms)
- Policy Compliance: LLM-as-judge (~500ms)
- Secrets: Pattern scanner (~5ms)

**Total**: ~1260ms (can run post-filters in parallel or async)

### Batch/Offline (Throughput Optimized)

All models can be used:
- No strict latency requirements
- Focus on accuracy and throughput
- Can use larger models (Llama Guard 3-8B, full policy LLM)

## KServe Deployment

### Option 1: Transformer Pattern (Recommended)

Deploy guardrails as KServe transformer:

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: aim-with-guardrails
spec:
  transformer:
    containers:
      - name: guardrail-transformer
        image: aim-guardrails:latest
        # Pre/post filter logic
  predictor:
    containers:
      - name: aim-inference
        image: aim-inference:latest
        resources:
          requests:
            amd.com/gpu: "1"
```

### Option 2: Standalone Service

Deploy guardrails as separate service, AIM calls it:

```yaml
# Guardrail service
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: aim-guardrail-service
spec:
  predictor:
    containers:
      - name: guardrail-service
        image: aim-guardrails:latest
```

AIM service calls guardrail service before/after inference.

## Request Flow

### Pre-Filter (Input)

```python
# In KServe transformer preprocess
def preprocess(inputs):
    prompt = inputs["instances"][0]["prompt"]
    use_case = inputs["instances"][0].get("use_case", "chat")
    
    # Check guardrails
    allowed, results = guardrail_service.check_request(
        prompt=prompt,
        use_case=use_case
    )
    
    if not allowed:
        return {"error": "Blocked by guardrails"}
    
    # Apply redactions
    # Return preprocessed input
    return inputs
```

### Post-Filter (Output)

```python
# In KServe transformer postprocess
def postprocess(inputs, response):
    model_response = response["outputs"][0]["data"]
    use_case = inputs["instances"][0].get("use_case", "chat")
    
    # Check guardrails
    allowed, results = guardrail_service.check_response(
        response=model_response,
        use_case=use_case
    )
    
    if not allowed:
        return {"error": "Response blocked"}
    
    # Apply redactions
    # Return postprocessed response
    return response
```

## Use Case Detection

Include use case in request metadata:

```json
{
  "instances": [{
    "prompt": "What is AI?",
    "use_case": "chat",  // or "rag", "code_gen", "batch"
    "user_id": "user123",
    "metadata": {}
  }]
}
```

The guardrail service will:
1. Select optimized models based on use case
2. Enforce latency budget
3. Log latency metrics

## Latency Monitoring

Metrics exposed at `/metrics`:

- `guardrail_check_duration_seconds{use_case="chat"}` - Latency by use case
- `guardrail_latency_budget_exceeded_total{use_case="chat"}` - Budget violations
- `guardrail_requests_total{use_case="chat"}` - Request count by use case

## Performance Optimization

### Parallel Execution

For post-filters with larger budgets, run checks in parallel:

```python
import asyncio

async def check_response_parallel(response, use_case):
    tasks = [
        check_toxicity(response),
        check_pii(response),
        check_policy(response)
    ]
    results = await asyncio.gather(*tasks)
    return results
```

### Async Post-Filters

For non-blocking post-filters:

```python
# Run post-filters asynchronously
# Return response immediately, apply filters in background
# Log violations but don't block
```

### Model Caching

- Cache model predictions for identical inputs
- Use Redis or in-memory cache
- TTL based on use case

## Deployment Examples

### Chat Endpoint

```bash
# Deploy with chat-optimized configuration
kubectl apply -f k8s/kserve/aim-chat-with-guardrails.yaml
```

### RAG Endpoint

```bash
# Deploy with RAG-optimized configuration
kubectl apply -f k8s/kserve/aim-rag-with-guardrails.yaml
```

### Code Generation Endpoint

```bash
# Deploy with code-gen optimized configuration
kubectl apply -f k8s/kserve/aim-codegen-with-guardrails.yaml
```

## Testing Latency

```bash
# Test chat endpoint
curl -X POST http://aim-chat-with-guardrails:8080/v1/models/chat:predict \
  -H "Content-Type: application/json" \
  -d '{
    "instances": [{
      "prompt": "What is AI?",
      "use_case": "chat"
    }]
  }'

# Check latency metrics
curl http://aim-guardrail-service:9090/metrics | grep guardrail_check_duration
```

## Troubleshooting

### Latency Exceeds Budget

1. Check which models are being used
2. Verify use case is correctly specified
3. Consider using smaller/faster models
4. Enable async post-filters for non-critical checks

### Models Not Loading

1. Check resource limits (memory/CPU)
2. Verify models are downloaded
3. Check logs for import errors
4. Use fallback models if available

## Best Practices

1. **Specify use case** in every request for optimal model selection
2. **Monitor latency** metrics to ensure budgets are met
3. **Use async post-filters** for non-critical checks in tight budgets
4. **Cache predictions** for identical inputs
5. **Scale horizontally** for high-throughput scenarios

