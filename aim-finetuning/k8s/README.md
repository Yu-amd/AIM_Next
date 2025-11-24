# Kubernetes Integration for AIM Fine-Tuning

This directory contains Kubernetes resources for managing fine-tuning jobs.

## Components

### Custom Resource Definition (CRD)

- **`crd/finetuning-job-crd.yaml`**: Defines the `FineTuningJob` custom resource

### Controller

- **`controller/finetuning_controller.py`**: Kubernetes controller that watches and manages FineTuningJob resources

### Operator

- **`operator/finetuning-operator.yaml`**: Deployment, ServiceAccount, and RBAC for the controller

### Examples

- **`examples/finetuning-job-example.yaml`**: Example FineTuningJob resource

## Installation

### 1. Install CRD

```bash
kubectl apply -f k8s/crd/finetuning-job-crd.yaml
```

### 2. Deploy Operator

```bash
# Create namespace
kubectl create namespace aim-finetuning

# Deploy operator
kubectl apply -f k8s/operator/finetuning-operator.yaml
```

### 3. Verify Installation

```bash
# Check CRD
kubectl get crd finetuningjobs.aim.amd.com

# Check operator
kubectl get deployment -n aim-finetuning finetuning-operator

# Check controller logs
kubectl logs -n aim-finetuning -l app=finetuning-operator -f
```

## Usage

### Create a Fine-Tuning Job

```bash
kubectl apply -f k8s/examples/finetuning-job-example.yaml
```

### Monitor Job Status

```bash
# Get job status
kubectl get finetuningjob qwen-lora-finetune -n aim-finetuning

# Describe job
kubectl describe finetuningjob qwen-lora-finetune -n aim-finetuning

# Watch job
kubectl get finetuningjob qwen-lora-finetune -n aim-finetuning -w
```

### Check Pod Logs

```bash
# Get pod name
kubectl get pods -n aim-finetuning -l job=qwen-lora-finetune

# View logs
kubectl logs -n aim-finetuning <pod-name> -f
```

### Delete Job

```bash
kubectl delete finetuningjob qwen-lora-finetune -n aim-finetuning
```

## FineTuningJob Spec

See `crd/finetuning-job-crd.yaml` for the complete schema. Key fields:

- **baseModel**: Base model configuration
- **method**: Fine-tuning method (lora, qlora, full)
- **dataset**: Dataset source and format
- **hyperparameters**: Training hyperparameters
- **loraConfig**: LoRA-specific configuration (for lora/qlora methods)
- **quantizationConfig**: Quantization configuration (for qlora method)
- **output**: Output configuration
- **resources**: Kubernetes resource requests/limits

## Status Fields

The FineTuningJob status includes:

- **phase**: Current phase (Pending, Running, Succeeded, Failed, Paused)
- **startTime**: Job start timestamp
- **completionTime**: Job completion timestamp
- **currentEpoch**: Current training epoch
- **totalEpochs**: Total epochs
- **trainLoss**: Current training loss
- **checkpointPath**: Path to latest checkpoint
- **modelPath**: Path to final model
- **aimProfilePath**: Path to AIM profile
- **message**: Status message
- **conditions**: Array of condition objects

## Development

### Build Controller Image

```bash
docker build -t aim-finetuning-controller:latest -f k8s/controller/Dockerfile .
```

### Run Controller Locally

```bash
# Set up kubeconfig
export KUBECONFIG=~/.kube/config

# Run controller
python3 k8s/controller/finetuning_controller.py
```

