# Monitoring & Validation Framework

This document describes the monitoring and validation features for fine-tuning jobs.

## Overview

Phase 3 of the fine-tuning module adds:
- **Prometheus metrics export** - Real-time training metrics and job status
- **Validation framework** - Quality checks and model validation

## Prometheus Metrics

### Metrics Exporter

The `FineTuningMetricsExporter` class exposes fine-tuning metrics via Prometheus:

```python
from finetuning.monitoring.metrics import FineTuningMetricsExporter

exporter = FineTuningMetricsExporter(port=8000)
exporter.start_server()
```

### Available Metrics

#### Job Status Metrics
- `finetuning_job_status` - Job status (0=Pending, 1=Running, 2=Succeeded, 3=Failed, 4=Paused)
- `finetuning_job_duration_seconds` - Job duration histogram

#### Training Progress Metrics
- `finetuning_training_epoch` - Current training epoch
- `finetuning_training_step` - Current training step
- `finetuning_training_progress` - Training progress percentage (0-100)

#### Training Performance Metrics
- `finetuning_train_loss` - Current training loss
- `finetuning_learning_rate` - Current learning rate
- `finetuning_samples_per_second` - Training throughput
- `finetuning_tokens_per_second` - Token throughput

#### Resource Utilization Metrics
- `finetuning_gpu_utilization_percent` - GPU utilization percentage
- `finetuning_gpu_memory_used_bytes` - GPU memory used
- `finetuning_gpu_memory_total_bytes` - Total GPU memory

#### Checkpoint Metrics
- `finetuning_checkpoints_total` - Total checkpoints saved
- `finetuning_checkpoint_size_bytes` - Checkpoint size histogram

### Usage in Training Script

Enable metrics export when running training:

```bash
python3 -m finetuning.base.app \
  --model-id Qwen/Qwen2.5-7B-Instruct \
  --dataset-path templates/example_dataset.jsonl \
  --output-dir ./output \
  --method lora \
  --enable-metrics \
  --metrics-port 8000
```

Metrics will be available at `http://localhost:8000/metrics`.

### Standalone Metrics Server

Run a standalone metrics server:

```bash
python3 -m finetuning.monitoring.metrics_server \
  --port 8000 \
  --job-name my-job \
  --model-id Qwen/Qwen2.5-7B-Instruct \
  --method lora \
  --training-info ./output/training_info.json
```

## Validation Framework

### Validator

The `FineTuningValidator` class provides quality checks for fine-tuning jobs:

```python
from finetuning.monitoring.validators.validator import FineTuningValidator

validator = FineTuningValidator()
results = validator.run_all_checks(
    training_info=training_info,
    model_path="./output",
    checkpoint_path="./checkpoints",
    profile_path="./output/aim_profile.json"
)
```

### Validation Checks

1. **Training Loss Validation**
   - Validates loss is within expected range
   - Checks if loss is decreasing

2. **Model Output Validation**
   - Tests model can generate outputs
   - Validates outputs contain expected keywords

3. **Checkpoint Integrity**
   - Validates checkpoint files are complete
   - Checks JSON files are readable

4. **AIM Profile Validation**
   - Validates profile format
   - Checks required fields are present
   - Validates memory values are positive

### Usage

Run validation on a completed training job:

```bash
python3 -m finetuning.monitoring.validate_job \
  --training-info ./output/training_info.json \
  --model-path ./output \
  --checkpoint-path ./checkpoints \
  --profile-path ./output/aim_profile.json \
  --output validation_report.txt
```

### Validation Report

The validator generates a report:

```
=== Fine-Tuning Validation Report ===

✓ PASS - training_loss
  Training loss: 0.5234
  Score: 0.5234

✓ PASS - checkpoint_integrity
  Checkpoint files are valid and complete

✓ PASS - aim_profile
  AIM profile is valid

Summary: 3/3 checks passed
```

## Remote Access via SSH Port Forwarding

When running training on a remote server, you can access the Prometheus metrics endpoint using SSH port forwarding.

### Setup SSH Port Forwarding

From your local machine, establish an SSH tunnel to forward the metrics port:

```bash
# Forward remote port 8000 to local port 8000
ssh -L 8000:localhost:8000 user@remote-server

# Or use a different local port (e.g., 9000)
ssh -L 9000:localhost:8000 user@remote-server

# Keep the connection alive and run in background
ssh -f -N -L 8000:localhost:8000 user@remote-server
```

**Parameters:**
- `-L local_port:remote_host:remote_port` - Local port forwarding
- `-f` - Run in background
- `-N` - Don't execute remote commands (just forward ports)

### Access Metrics Remotely

Once the SSH tunnel is established, access metrics from your local machine:

```bash
# If using local port 8000
curl http://localhost:8000/metrics

# If using local port 9000
curl http://localhost:9000/metrics
```

### Validation Steps

1. **Verify SSH tunnel is active:**
```bash
# Check if SSH process is running
ps aux | grep "ssh.*-L.*8000"

# Or check if port is listening locally
netstat -tlnp | grep 8000
# or
ss -tlnp | grep 8000
```

2. **Test metrics endpoint through tunnel:**
```bash
# Basic connectivity test
curl -s http://localhost:8000/metrics | head -20

# Check for fine-tuning metrics
curl -s http://localhost:8000/metrics | grep finetuning

# Get specific metric
curl -s http://localhost:8000/metrics | grep "finetuning_job_status"
```

3. **Verify metrics are updating:**
```bash
# Watch metrics in real-time (refresh every 5 seconds)
watch -n 5 'curl -s http://localhost:8000/metrics | grep finetuning | head -10'
```

4. **Test from browser:**
   - Open `http://localhost:8000/metrics` in your browser
   - You should see Prometheus metrics in plain text format
   - Search for `finetuning` to find fine-tuning specific metrics

### Troubleshooting SSH Port Forwarding

**Issue: "Address already in use"**
```bash
# Check what's using the port
lsof -i :8000
# or
netstat -tlnp | grep 8000

# Use a different local port
ssh -L 9000:localhost:8000 user@remote-server
```

**Issue: "Connection refused"**
- Verify the metrics server is running on the remote host
- Check the metrics port matches (default is 8000)
- Ensure firewall allows the connection

**Issue: "Permission denied"**
- Verify SSH key authentication is set up
- Check SSH config allows port forwarding (default: yes)

**Issue: Metrics not updating**
- Ensure training is actively running
- Check metrics exporter is enabled (`--enable-metrics` flag)
- Verify metrics server started successfully (check logs)

### Quick Validation Script

A validation script is provided to test SSH port forwarding and metrics access:

```bash
# Run validation script (default port 8000)
./validate_metrics_remote.sh

# Or specify a different port
./validate_metrics_remote.sh 9000
```

The script checks:
- SSH tunnel is active
- Metrics endpoint is accessible
- Fine-tuning metrics are present
- Specific metric types are available

### Example: Complete Remote Monitoring Workflow

1. **On remote server, start training with metrics:**
```bash
cd /root/AIM_Next/aim-finetuning
python3 -m finetuning.base.app \
  --model-id Qwen/Qwen2.5-7B-Instruct \
  --dataset-path templates/example_dataset.jsonl \
  --output-dir ./output \
  --method lora \
  --enable-metrics \
  --metrics-port 8000
```

2. **On local machine, establish SSH tunnel:**
```bash
ssh -f -N -L 8000:localhost:8000 user@remote-server
```

3. **Validate connection:**
```bash
# Test endpoint
curl http://localhost:8000/metrics | grep finetuning

# Expected output should include metrics like:
# finetuning_job_status{job_name="...", model_id="...", method="lora"} 1.0
# finetuning_train_loss{job_name="...", model_id="...", epoch="1"} 0.5234
```

4. **Monitor in real-time:**
```bash
# Watch metrics update
watch -n 5 'curl -s http://localhost:8000/metrics | grep finetuning'
```

5. **Configure Prometheus to scrape (optional):**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'finetuning'
    static_configs:
      - targets: ['localhost:8000']  # Through SSH tunnel
```

### Security Considerations

- SSH port forwarding is encrypted end-to-end
- Only forward ports you need
- Close SSH tunnels when not in use
- Consider using SSH config for persistent tunnels:
```bash
# ~/.ssh/config
Host finetuning-server
    HostName remote-server
    User your-username
    LocalForward 8000 localhost:8000
```

Then connect with: `ssh finetuning-server`

## Integration with Kubernetes

### Metrics Sidecar

Add a metrics sidecar to your training pod:

```yaml
containers:
  - name: finetuning
    # ... training container ...
  
  - name: metrics
    image: aim-finetuning:latest
    command: ["python3", "-m", "finetuning.monitoring.metrics_server"]
    args:
      - "--port"
      - "8000"
      - "--job-name"
      - "$(JOB_NAME)"
      - "--model-id"
      - "$(MODEL_ID)"
      - "--method"
      - "$(METHOD)"
      - "--training-info"
      - "/workspace/output/training_info.json"
    ports:
      - containerPort: 8000
        name: metrics
```

### Prometheus ServiceMonitor

Create a ServiceMonitor for Prometheus to scrape metrics:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: finetuning-metrics
  namespace: aim-finetuning
spec:
  selector:
    matchLabels:
      app: finetuning-metrics
  endpoints:
    - port: metrics
      interval: 30s
```

## Example: Complete Workflow

1. **Start training with metrics**:
```bash
python3 -m finetuning.base.app \
  --model-id Qwen/Qwen2.5-7B-Instruct \
  --dataset-path templates/example_dataset.jsonl \
  --output-dir ./output \
  --method lora \
  --enable-metrics \
  --metrics-port 8000
```

2. **Monitor metrics** (in another terminal):
```bash
curl http://localhost:8000/metrics | grep finetuning
```

3. **Validate after training**:
```bash
python3 -m finetuning.monitoring.validate_job \
  --training-info ./output/training_info.json \
  --model-path ./output \
  --profile-path ./output/aim_profile.json
```

## Dependencies

Install monitoring dependencies:

```bash
pip install prometheus-client --break-system-packages
```

The `prometheus-client` package is included in `requirements.txt`.

## Troubleshooting

- **Metrics not available**: Ensure `prometheus-client` is installed and metrics server is running
- **Validation fails**: Check that all required files exist and are readable
- **GPU metrics unavailable**: GPU metrics require `amd-smi` to be available

