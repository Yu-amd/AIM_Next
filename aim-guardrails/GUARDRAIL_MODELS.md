# Guardrail Models Reference

This document describes the available models for each guardrail type and how to configure them.

## Model Selection

The guardrail service supports multiple models for each guardrail type. Configure which model to use in `guardrails/core/guardrail_config.yaml`.

## 1. Safety / Toxicity / Abuse Filter

### Available Models

#### RoBERTa Toxicity Classifier (Recommended)
- **Model**: `s-nlp/roberta_toxicity_classifier`
- **Type**: Text classifier (RoBERTa-based)
- **Speed**: Fast (~10-50ms on CPU)
- **Accuracy**: High
- **Use Case**: Primary toxicity filter

#### Detoxify (Fallback)
- **Model**: `unitary/toxic-bert` (via Detoxify library)
- **Type**: Multi-head toxicity model
- **Speed**: Medium (~50-200ms)
- **Accuracy**: High
- **Use Case**: Fallback or multilingual support

#### XLM-RoBERTa Toxicity (Multilingual)
- **Model**: `textdetox/xlmr-large-toxicity-classifier`
- **Type**: Multilingual toxicity classifier
- **Speed**: Medium (~50-200ms)
- **Accuracy**: High for multiple languages
- **Use Case**: Multilingual deployments

### Configuration

```yaml
toxicity:
  model: roberta_toxicity  # or detoxify, xlm_toxicity
  fallback: detoxify
  pre_filter: true
  post_filter: true
  threshold: 0.7
```

### Actions

- `block`: Block request/response (hard threshold)
- `allow_with_warning`: Allow but log/watermark (soft threshold)
- `allow`: Allow if below threshold

## 2. PII / Privacy / Data-Leakage Filter

### Available Models

#### Piiranha (Recommended)
- **Model**: `iiiorg/piiranha-v1-detect-personal-information`
- **Type**: Multilingual PII detector (17 PII types, 6 languages)
- **Speed**: Medium (~100-300ms)
- **Accuracy**: High
- **Use Case**: Primary PII detection

#### Presidio (Fallback)
- **Model**: Microsoft Presidio (spaCy NER + custom models)
- **Type**: Rule-based + ML NER
- **Speed**: Fast (~50-150ms)
- **Accuracy**: High for structured PII
- **Use Case**: Fallback or structured data

#### ab-ai/pii_model
- **Model**: `ab-ai/pii_model`
- **Type**: BERT token classifier
- **Speed**: Medium (~100-200ms)
- **Accuracy**: Good
- **Use Case**: Alternative PII detection

#### Phi-3 Mini PII
- **Model**: `ab-ai/PII-Model-Phi3-Mini`
- **Type**: Generative PII classifier
- **Speed**: Medium (~200-500ms)
- **Accuracy**: High
- **Use Case**: Generative PII detection

### Configuration

```yaml
pii:
  model: piiranha  # or presidio, ab_ai_pii, phi3_pii
  fallback: presidio
  pre_filter: true  # Check input for disallowed PII
  post_filter: true   # Redact PII in output
  threshold: 0.8
```

### Actions

- `redact`: Remove/mask PII (default for output)
- `block`: Block if PII detected in input (for external APIs)

## 3. Prompt Injection / Jailbreak Detection

### Available Models

#### ProtectAI DeBERTa (Recommended)
- **Model**: `protectai/deberta-v3-base-prompt-injection-v2`
- **Type**: Binary classifier (injection vs benign)
- **Speed**: Fast (~20-100ms)
- **Accuracy**: Very high
- **Use Case**: Primary prompt injection filter

#### Enhanced Pattern (Fallback)
- **Type**: Pattern matching + semantic similarity
- **Speed**: Fast (~10-50ms)
- **Accuracy**: Good
- **Use Case**: Fallback or lightweight deployment

### Configuration

```yaml
prompt_injection:
  model: protectai_deberta  # or enhanced_pattern
  fallback: enhanced_pattern
  pre_filter: true   # Only check input
  post_filter: false
  threshold: 0.75
```

### Actions

- `block`: Block injection attempts (default)
- `allow_with_warning`: Log but allow (for testing)

## 4. All-in-One Safety Judge

### Available Models

#### Llama Guard 3 (Recommended)
- **Model**: `meta-llama/LlamaGuard-3-8B` or `meta-llama/LlamaGuard-3-1B`
- **Type**: Comprehensive safety classifier
- **Speed**: Medium (~200-1000ms, depends on GPU)
- **Accuracy**: Very high
- **Coverage**: Toxicity, self-harm, sexual, jailbreak, etc.
- **Use Case**: Primary safety judge for post-filter

#### Llama Guard 2
- **Model**: `meta-llama/LlamaGuard-2-8B`
- **Type**: Safety classifier (Llama 3-based)
- **Speed**: Medium (~200-1000ms)
- **Accuracy**: High
- **Use Case**: Alternative to Llama Guard 3

#### Granite Guardian (Future)
- **Model**: IBM Granite Guardian models
- **Type**: Risk detection models
- **Coverage**: Jailbreaks, profanity, hallucinations, tool/RAG misuse
- **Use Case**: Enterprise risk detection

### Configuration

```yaml
all_in_one_judge:
  model: llama_guard
  model_name: "meta-llama/LlamaGuard-3-8B"  # or 1B for faster
  pre_filter: true
  post_filter: true
  optional: true  # Can run alongside specific checkers
  threshold: 0.7
```

## 5. Policy / Compliance Filter

### Available Models

#### LLM-as-Judge (Recommended)
- **Model**: Small LLM (Qwen2.5-3B, Phi-3-mini, Llama-3.2-3B)
- **Type**: Policy judgment via few-shot prompting
- **Speed**: Medium (~500-2000ms)
- **Accuracy**: High for custom policies
- **Use Case**: Enterprise-specific policy enforcement

### Configuration

```yaml
policy_compliance:
  model: policy_llm
  model_name: "Qwen/Qwen2.5-3B-Instruct"
  pre_filter: false
  post_filter: true  # Check output against policies
  threshold: 0.7
```

### Custom Policy Rules

Define policy rules in the checker initialization or via configuration:

```python
policy_rules = """
Policy Rules:
1. Do not mention confidential product roadmaps
2. Do not provide financial guidance
3. Ensure regulatory compliance
"""
```

## 6. Secrets / IP / Code Safety Filter

### Available Models

#### Secret Scanner (Pattern-Based)
- **Type**: Pattern matching + entropy analysis
- **Speed**: Very fast (~1-10ms)
- **Accuracy**: High for common patterns
- **Patterns**: API keys, AWS keys, GitHub tokens, private keys, passwords
- **Use Case**: Code generation endpoints, input/output scanning

### Configuration

```yaml
secrets:
  model: secret_scanner
  pre_filter: true
  post_filter: true  # Especially for code models
  threshold: 0.7
```

## Recommended Configuration for AIM

Based on your requirements, here's the recommended setup:

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

## Model Loading and Performance

### CPU vs GPU

- **CPU**: Suitable for small models (RoBERTa, DeBERTa, pattern-based)
  - Latency: 10-200ms per check
  - No GPU required

- **GPU**: Recommended for larger models (Llama Guard, policy LLMs)
  - Latency: 200-2000ms per check
  - Better throughput for batch processing

### Model Caching

Models are loaded on service startup:
- First startup: Downloads models (~2-5 minutes)
- Subsequent startups: Loads cached models (~30-60 seconds)

For production, consider:
- Pre-downloading models in Docker image
- Using model caching volumes
- Lazy loading for optional models

## Fallback Strategy

The service implements automatic fallback:
1. Try primary model (e.g., RoBERTa toxicity)
2. If unavailable, try fallback model (e.g., Detoxify)
3. If still unavailable, use pattern-based checker
4. If all fail, allow content but log warning

This ensures service availability even if models fail to load.

