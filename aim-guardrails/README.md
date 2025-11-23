# AIM Guardrail Microservices

Production-ready safety and filtering layers that can be deployed alongside AIM inference endpoints to ensure responsible AI deployments.

## Features

- Multiple guardrail models optimized for different safety concerns
- Compatible with AIM Inference Microservice architecture
- Configurable safety policies and thresholds
- Real-time content filtering and response validation
- Sidecar and proxy deployment patterns

## Supported Guardrail Types

- **Toxicity Detection** - Detect harmful or toxic content
- **PII Detection** - Detect and redact personally identifiable information
- **Prompt Injection** - Detect prompt injection attacks
- **NSFW Filter** - Filter not-safe-for-work content
- **Bias Detection** - Identify biased or discriminatory content
- **Jailbreak Detection** - Detect attempts to bypass safety measures

## Architecture

See the main [prototype recommendations document](../AIM_next_prototype_recommendations.md#2-aim-guardrail-microservices-prototype) for detailed architecture.

## Directory Structure

```
aim-guardrails/
├── guardrails/           # Guardrail implementations
│   ├── base/            # Base guardrail container
│   ├── toxicity/        # Toxicity detection
│   ├── pii/             # PII detection
│   ├── prompt_injection/ # Prompt injection detection
│   └── nsfw/            # NSFW filtering
├── orchestrator/        # Multi-guardrail orchestration
├── k8s/                 # Kubernetes resources
├── profiles/            # AIM profiles for guardrails
└── monitoring/          # Metrics and dashboards
```

## Development Status

🚧 In Development


