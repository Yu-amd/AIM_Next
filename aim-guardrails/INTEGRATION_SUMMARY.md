# Guardrails Integration Summary

## Complete Implementation

All refined guardrail requirements have been integrated into the production-ready implementation.

## Filter Types Implemented

### 1. Safety / Toxicity / Abuse Filter ✅

**Primary Model**: `s-nlp/roberta_toxicity_classifier`
- Fast RoBERTa-based toxicity classifier
- Multi-label classification
- Pre-filter and post-filter support

**Fallback Models**:
- Detoxify (Unitary) - Multi-head toxicity model
- XLM-RoBERTa - Multilingual support

**Actions**: `block`, `allow_with_warning`, `allow`

### 2. PII / Privacy / Data-Leakage Filter ✅

**Primary Model**: `iiiorg/piiranha-v1-detect-personal-information`
- Multilingual PII detection (17 types, 6 languages)
- Token-level classification
- Automatic redaction

**Fallback Models**:
- Presidio (Microsoft) - Rule-based + ML NER
- ab-ai/pii_model - BERT token classifier
- ab-ai/PII-Model-Phi3-Mini - Generative PII detection

**Actions**: `redact` (output), `block` (input for external APIs)

### 3. Prompt Injection / Jailbreak Detection ✅

**Primary Model**: `protectai/deberta-v3-base-prompt-injection-v2`
- Binary classifier (injection vs benign)
- Fast, accurate detection
- Pre-filter only (input side)

**Fallback**: Enhanced pattern matching with semantic similarity

**Actions**: `block` (default)

### 4. All-in-One Safety Judge ✅

**Primary Model**: `meta-llama/LlamaGuard-3-8B` (or 1B for faster)
- Comprehensive safety classification
- Multiple harm categories (toxicity, self-harm, sexual, jailbreak, etc.)
- MLCommons hazard taxonomy
- Pre-filter and post-filter support

**Alternatives**: Llama Guard 2, Granite Guardian (future)

**Actions**: `block`, `allow_with_warning`

### 5. Policy / Compliance Filter ✅

**Primary Model**: LLM-as-judge pattern
- Small LLMs: Qwen2.5-3B, Phi-3-mini, Llama-3.2-3B-Instruct
- Custom enterprise policy enforcement
- Few-shot prompting for policy rules
- Post-filter (checks output against policies)

**Actions**: `block`, `modify`, `allow_with_warning`

### 6. Secrets / IP / Code Safety Filter ✅

**Type**: Pattern-based scanner (Gitleaks/TruffleHog-style)
- Detects API keys, tokens, private keys, passwords
- Entropy analysis for high-entropy strings
- Pattern matching for common secret formats
- Pre-filter and post-filter (especially for code models)

**Actions**: `block`, `redact`

### 7. Traffic-Level Guardrails ✅

**Non-ML guardrails** for traffic management:
- Rate limiting (per-minute, per-hour, per-day)
- Context length limits
- Upload size limits
- Geo restrictions
- Business hours access control

## Recommended AIM Deployment Pattern

### Pre-Filters (on user prompt)

1. **Prompt Injection**: `protectai/deberta-v3-base-prompt-injection-v2`
   - Fast binary gate
   - Blocks injection attempts

2. **Toxicity**: `s-nlp/roberta_toxicity_classifier`
   - Fast toxicity check
   - Blocks or warns on toxic content

3. **PII**: `iiiorg/piiranha-v1-detect-personal-information`
   - Detects PII in input
   - Blocks if crossing tenant/network boundaries

4. **Secrets**: Pattern-based scanner
   - Detects secrets in input
   - Blocks if detected

5. **Rate Limits**: Traffic-level guardrails
   - Context length limits
   - Upload size limits
   - Request rate limits

### Post-Filters (on AIM response)

1. **All-in-One Judge**: `meta-llama/LlamaGuard-3-8B`
   - Comprehensive safety check
   - Covers multiple harm categories

2. **PII Redaction**: `iiiorg/piiranha-v1` or `presidio`
   - Redacts PII in output
   - Provides sanitized response

3. **Policy Compliance**: `Qwen/Qwen2.5-3B-Instruct` (LLM-as-judge)
   - Checks against enterprise policies
   - Can rewrite or refuse

4. **Secrets**: Pattern-based scanner
   - Scans code outputs for secrets
   - Attaches warnings or blocks

## Configuration

Configure models in `guardrails/core/guardrail_config.yaml`:

```yaml
guardrails:
  toxicity:
    model: roberta_toxicity
    fallback: detoxify
    pre_filter: true
    post_filter: true
    
  pii:
    model: piiranha
    fallback: presidio
    pre_filter: true
    post_filter: true
    
  prompt_injection:
    model: protectai_deberta
    fallback: enhanced_pattern
    pre_filter: true
    post_filter: false
    
  all_in_one_judge:
    model: llama_guard
    model_name: "meta-llama/LlamaGuard-3-8B"
    optional: true
```

## API Usage

### Check Request (Pre-Filter)

```bash
curl -X POST http://localhost:8080/check/request \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is AI?",
    "user_id": "user123",
    "context_length": 100,
    "geo": "US"
  }'
```

### Check Response (Post-Filter)

```bash
curl -X POST http://localhost:8080/check/response \
  -H "Content-Type: application/json" \
  -d '{
    "response": "Model response text",
    "original_prompt": "What is AI?"
  }'
```

## Deployment

### Docker

```bash
docker build -t aim-guardrails:latest .
docker run -d \
  -p 8080:8080 -p 9090:9090 \
  -e ENABLE_METRICS=true \
  -e GUARDRAIL_CONFIG_YAML=/etc/guardrails/config.yaml \
  -v $(pwd)/guardrails/core/guardrail_config.yaml:/etc/guardrails/config.yaml:ro \
  aim-guardrails:latest
```

### Kubernetes

```bash
kubectl apply -f k8s/deployment/guardrail-deployment.yaml
kubectl apply -f k8s/monitoring/service-monitor.yaml
```

## Monitoring

Metrics available at `http://localhost:9090/metrics`:
- `guardrail_requests_total` - Total checks
- `guardrail_requests_blocked_total` - Blocked requests
- `guardrail_check_duration_seconds` - Latency
- `guardrail_confidence_score` - Detection confidence
- `guardrail_model_available` - Model status

## Performance

- **Small models (CPU)**: 10-200ms per check
- **Medium models (CPU/GPU)**: 50-500ms per check
- **Large models (GPU)**: 200-2000ms per check

Choose models based on latency requirements and accuracy needs.

