# Next Steps for GPU Sharing Implementation

## Current Status

### ✅ Phase 1: Foundation - COMPLETED

- [x] ROCm memory partitioning layer (`rocm_partitioner.py`)
- [x] Model scheduler (`model_scheduler.py`)
- [x] Resource isolator (`resource_isolator.py`)
- [x] Model sizing configuration with precision support (FP16, INT8, INT4)
- [x] AIM profile generation (114 profiles for 38 models)
- [x] Comprehensive unit test suite (61 tests, all passing)

## Next Steps

### Phase 2: Integration (Weeks 3-4)

#### 1. KServe CRD Extension (Priority: High)

**Location**: `k8s/crd/gpu-sharing-crd.yaml`

**Tasks**:
- [ ] Define extended InferenceService CRD with GPU sharing annotations
- [ ] Add validation webhooks for partition allocation
- [ ] Create CRD schema for GPU sharing configuration

**Example structure**:
```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: inferenceservices.aim.amd.com
spec:
  # Extend existing KServe InferenceService
  # Add GPU sharing fields
```

**Files to create**:
- `k8s/crd/gpu-sharing-crd.yaml`
- `k8s/crd/schema.yaml` (OpenAPI schema)
- `k8s/crd/webhook.yaml` (validation webhook)

#### 2. Kubernetes Partition Controller (Priority: High)

**Location**: `k8s/controller/partition_controller.py`

**Tasks**:
- [ ] Implement K8s controller using kubebuilder or operator-sdk
- [ ] Watch for InferenceService CRs with GPU sharing annotations
- [ ] Allocate partitions using `rocm_partitioner`
- [ ] Update InferenceService status with partition info
- [ ] Handle partition lifecycle (create, update, delete)

**Key features**:
- Reconcile loop for partition management
- Event handling for CRD changes
- Integration with model scheduler
- Error handling and retry logic

**Files to create**:
- `k8s/controller/partition_controller.py`
- `k8s/controller/main.py` (controller entry point)
- `k8s/controller/Dockerfile`
- `k8s/controller/requirements.txt`

#### 3. GPU Sharing Operator (Priority: Medium)

**Location**: `k8s/operator/`

**Tasks**:
- [ ] Create operator manifest (Deployment, ServiceAccount, RBAC)
- [ ] Configure operator to run partition controller
- [ ] Set up monitoring and health checks
- [ ] Create installation manifests

**Files to create**:
- `k8s/operator/gpu-sharing-operator.yaml`
- `k8s/operator/rbac.yaml`
- `k8s/operator/deployment.yaml`
- `k8s/operator/install.sh` (installation script)

#### 4. Metrics Exporter (Priority: Medium)

**Location**: `monitoring/metrics_exporter.py`

**Tasks**:
- [ ] Implement Prometheus metrics exporter
- [ ] Expose partition metrics (memory usage, utilization)
- [ ] Expose model metrics (latency, throughput)
- [ ] Add metrics for scheduler operations
- [ ] Create metrics endpoint (/metrics)

**Metrics to expose**:
- `aim_gpu_partition_memory_bytes` - Memory usage per partition
- `aim_gpu_partition_utilization` - Compute utilization per partition
- `aim_model_request_latency_seconds` - Request latency per model
- `aim_model_requests_total` - Total requests per model
- `aim_scheduler_operations_total` - Scheduler operation counts

**Files to create**:
- `monitoring/metrics_exporter.py`
- `monitoring/metrics.py` (metric definitions)
- `monitoring/Dockerfile`

### Phase 3: QoS & Monitoring (Weeks 5-6)

#### 5. QoS Framework (Priority: Medium)

**Location**: `runtime/qos_manager.py`

**Tasks**:
- [ ] Implement priority-based request scheduling
- [ ] Add minimum/maximum resource guarantees
- [ ] Track latency SLOs per model
- [ ] Implement request queuing
- [ ] Add throttling for low-priority requests

**Files to create**:
- `runtime/qos_manager.py`
- `runtime/request_queue.py`
- `tests/test_qos_manager.py`

#### 6. Grafana Dashboards (Priority: Low)

**Location**: `monitoring/dashboards/`

**Tasks**:
- [ ] Create dashboard for partition utilization
- [ ] Create dashboard for model performance
- [ ] Create dashboard for scheduler metrics
- [ ] Add alerts for resource exhaustion

**Files to create**:
- `monitoring/dashboards/partition-utilization.json`
- `monitoring/dashboards/model-performance.json`
- `monitoring/dashboards/scheduler-metrics.json`

## Implementation Order

### Recommended Sequence

1. **Metrics Exporter** (Start here - enables monitoring)
   - Quick win, provides visibility
   - Can be developed in parallel with other components
   - Helps validate other components

2. **KServe CRD Extension**
   - Foundation for K8s integration
   - Defines the API contract
   - Needed before controller

3. **Partition Controller**
   - Core integration component
   - Uses CRD and runtime components
   - Most complex, needs careful design

4. **GPU Sharing Operator**
   - Packaging and deployment
   - Depends on controller
   - Makes everything deployable

5. **QoS Framework**
   - Advanced feature
   - Enhances existing scheduler
   - Can be added incrementally

6. **Grafana Dashboards**
   - Visualization layer
   - Depends on metrics
   - Nice to have for operations

## Getting Started

### Option 1: Metrics Exporter (Recommended First)

```bash
cd aim-gpu-sharing/monitoring
# Create metrics_exporter.py
# Implement Prometheus metrics
# Add tests
```

### Option 2: KServe CRD Extension

```bash
cd aim-gpu-sharing/k8s/crd
# Create gpu-sharing-crd.yaml
# Define schema
# Add validation
```

### Option 3: Partition Controller

```bash
cd aim-gpu-sharing/k8s/controller
# Set up controller framework
# Implement reconcile logic
# Integrate with runtime components
```

## Development Guidelines

### For Each Component

1. **Create the component**
   - Follow existing code patterns
   - Use type hints
   - Add docstrings

2. **Write tests**
   - Unit tests first
   - Integration tests if needed
   - Update test suite

3. **Update documentation**
   - Component README
   - API documentation
   - Usage examples

4. **Integration**
   - Test with existing components
   - Update main README
   - Add to examples

## Dependencies

### For K8s Components

```bash
pip install kubernetes>=28.0.0
pip install kubeflow-kserve>=0.11.0
```

### For Controller Development

Consider using:
- **kubebuilder**: For CRD and controller scaffolding
- **operator-sdk**: Alternative framework
- **Plain Python**: Using kubernetes client library

## Questions to Consider

Before implementing each component:

1. **Metrics Exporter**:
   - What metrics are most valuable?
   - How to expose metrics (HTTP endpoint)?
   - How to integrate with Prometheus?

2. **CRD Extension**:
   - How to extend existing KServe CRD?
   - What validation is needed?
   - How to handle versioning?

3. **Controller**:
   - Which controller framework to use?
   - How to handle partition conflicts?
   - How to recover from failures?

4. **QoS**:
   - What priority levels?
   - How to enforce guarantees?
   - How to measure SLOs?

## Resources

- [KServe Documentation](https://kserve.github.io/website/)
- [Kubernetes Custom Resources](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/)
- [Prometheus Metrics](https://prometheus.io/docs/instrumenting/exposition_formats/)
- [Grafana Dashboard JSON](https://grafana.com/docs/grafana/latest/dashboards/json-model/)

---

**Ready to start?** Pick a component and begin implementation. Remember to:
- Write tests as you go
- Update documentation
- Follow existing patterns
- Ask questions if stuck

