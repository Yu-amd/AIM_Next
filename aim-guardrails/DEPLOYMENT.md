# Production Deployment Guide

Complete guide for deploying AIM Guardrails in production with Docker and Kubernetes.

## Prerequisites

- Docker installed
- Kubernetes cluster (for K8s deployment)
- kubectl configured
- Python 3.10+ (for local development)

## Docker Deployment

### Build Docker Image

```bash
cd aim-guardrails
docker build -t aim-guardrails:latest .
```

**Note**: First build will download ML models (~800MB total), which may take several minutes.

### Run Container

```bash
docker run -d \
  --name guardrail-service \
  -p 8080:8080 \
  -p 9090:9090 \
  -e ENABLE_METRICS=true \
  -e GUARDRAIL_CONFIG=/etc/guardrails/policy.json \
  -v $(pwd)/policy.json:/etc/guardrails/policy.json:ro \
  aim-guardrails:latest
```

### Verify Deployment

```bash
# Health check
curl http://localhost:8080/health

# Check metrics
curl http://localhost:9090/metrics | grep guardrail

# Test guardrail
curl -X POST http://localhost:8080/check/request \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is AI?"}'
```

## Kubernetes Deployment

### Step 1: Create Namespace

```bash
kubectl create namespace aim-guardrails
```

### Step 2: Deploy CRD

```bash
kubectl apply -f k8s/crd/guardrail-policy-crd.yaml
```

### Step 3: Create ConfigMap (Policy Configuration)

```bash
kubectl create configmap guardrail-policy-config \
  --from-file=policy.json=k8s/deployment/policy.json \
  -n aim-guardrails
```

Or create custom policy:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: guardrail-policy-config
  namespace: aim-guardrails
data:
  policy.json: |
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

### Step 4: Deploy Service

```bash
kubectl apply -f k8s/deployment/guardrail-deployment.yaml
```

### Step 5: Verify Deployment

```bash
# Check pods
kubectl get pods -n aim-guardrails

# Check logs
kubectl logs -n aim-guardrails -l app=aim-guardrail-service

# Port forward for testing
kubectl port-forward -n aim-guardrails svc/aim-guardrail-service 8080:8080 9090:9090
```

### Step 6: Deploy Monitoring (Optional)

```bash
# Deploy ServiceMonitor for Prometheus
kubectl apply -f k8s/monitoring/service-monitor.yaml
```

## Monitoring

### Prometheus Metrics

Metrics are available at `http://localhost:9090/metrics` (or via port-forward in K8s).

**Key Metrics**:
- `guardrail_requests_total{type="request",guardrail_type="toxicity"}` - Total checks
- `guardrail_requests_blocked_total` - Blocked requests
- `guardrail_check_duration_seconds` - Check latency (histogram)
- `guardrail_confidence_score` - Detection confidence
- `guardrail_model_available` - Model availability (1=available, 0=unavailable)

### Grafana Dashboard

Create a dashboard with:
- Request rate (requests/sec)
- Block rate (blocks/sec)
- Average check duration
- Confidence score distribution
- Model availability status

## Production Considerations

### Resource Management

The deployment includes:
- **Memory**: 1-2Gi (models require ~800MB)
- **CPU**: 500m-2000m (ML inference is CPU-intensive)

Adjust based on your workload:
- Higher traffic → increase CPU limits
- More models → increase memory limits

### Model Loading

Models are loaded on container startup:
- **First startup**: Downloads models (~2-5 minutes)
- **Subsequent startups**: Loads cached models (~30-60 seconds)

Consider:
- Pre-downloading models in Docker image
- Using init containers to download models
- Model caching in persistent volumes

### High Availability

For production:
- Deploy multiple replicas (update `replicas` in deployment)
- Use HorizontalPodAutoscaler for auto-scaling
- Configure pod disruption budgets

### Security

- Use secrets for sensitive configuration
- Enable TLS for API endpoints
- Restrict network policies
- Use service accounts with minimal permissions

## Troubleshooting

### Models Not Loading

```bash
# Check logs
kubectl logs -n aim-guardrails <pod-name>

# Common issues:
# - Insufficient memory (increase limits)
# - Network issues (check internet access)
# - Disk space (check available storage)
```

### High Memory Usage

Models require significant memory:
- Detoxify: ~500MB
- Presidio: ~200MB
- Sentence transformers: ~100MB
- Total: ~800MB base + overhead

If memory issues:
- Increase memory limits
- Use smaller models
- Enable model quantization

### Slow Response Times

ML inference adds latency:
- Toxicity check: ~50-200ms
- PII check: ~100-300ms
- Prompt injection: ~50-150ms

Optimize by:
- Using GPU acceleration (if available)
- Model quantization
- Caching frequent checks
- Batch processing

## Performance Tuning

### Model Selection

- **Detoxify**: Use `original` (default) or `unbiased` for different use cases
- **Presidio**: Configure entity types based on your needs
- **Sentence transformers**: Use smaller models for faster inference

### Caching

Implement caching for:
- Frequent prompts (cache toxicity/PII results)
- Model predictions (cache for identical inputs)

### Batch Processing

For high-throughput scenarios:
- Batch multiple checks together
- Use async processing
- Implement request queuing

## Health Checks

The service includes:
- **Liveness probe**: `/health` endpoint
- **Readiness probe**: `/health` endpoint
- **Startup probe**: Waits for models to load

Configure in deployment:
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 40  # Allow time for model loading
  periodSeconds: 30
```

## Scaling

### Horizontal Scaling

```bash
# Scale manually
kubectl scale deployment aim-guardrail-service --replicas=3 -n aim-guardrails

# Or use HPA
kubectl autoscale deployment aim-guardrail-service \
  --min=2 --max=10 \
  --cpu-percent=70 \
  -n aim-guardrails
```

### Vertical Scaling

Adjust resource limits in deployment based on:
- Request volume
- Model size
- Latency requirements

## Integration with Inference Endpoints

### Sidecar Pattern

Deploy guardrails as sidecar alongside inference service:

```yaml
containers:
  - name: inference
    image: inference-service:latest
  - name: guardrails
    image: aim-guardrails:latest
    env:
      - name: ENABLE_METRICS
        value: "true"
```

### Proxy Pattern

Use guardrails as proxy in front of inference:

```python
from guardrails.integration.inference_proxy import InferenceProxy

proxy = InferenceProxy(
    inference_endpoint="http://inference-service:8000/predict",
    guardrail_service=service
)
```

## Backup and Recovery

- **Policy configuration**: Store in version control
- **Model artifacts**: Cache in persistent volumes
- **Metrics**: Export to long-term storage

## Updates and Rollouts

```bash
# Rolling update
kubectl set image deployment/aim-guardrail-service \
  guardrail-service=aim-guardrails:v2.0 \
  -n aim-guardrails

# Monitor rollout
kubectl rollout status deployment/aim-guardrail-service -n aim-guardrails
```

