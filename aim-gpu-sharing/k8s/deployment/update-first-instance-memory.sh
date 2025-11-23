#!/bin/bash
#
# Update First vLLM Instance to Use Less Memory
#

set -e

MEMORY_UTIL="${1:-0.5}"  # Default 50%
NAMESPACE="aim-gpu-sharing"

echo "Updating first vLLM instance to use ${MEMORY_UTIL} GPU memory..."

# Get current deployment
kubectl get deployment vllm-model-deployment -n ${NAMESPACE} -o yaml > /tmp/first-deployment.yaml

# Update the args to include gpu-memory-utilization
python3 << EOF
import yaml
import sys

with open('/tmp/first-deployment.yaml', 'r') as f:
    deploy = yaml.safe_load(f)

# Find the container and update args
for container in deploy['spec']['template']['spec']['containers']:
    if container['name'] == 'vllm-server':
        # Update args to include memory utilization
        args_str = ' '.join(container.get('args', ['']))
        if '--gpu-memory-utilization' not in args_str:
            # Add it to the command
            if 'command' in container and container['command'] == ['/bin/bash', '-c']:
                new_args = container['args'][0] if container.get('args') else ''
                # Update the python command in the bash script
                import re
                new_args = re.sub(
                    r'--gpu-memory-utilization\s+[\d.]+',
                    f'--gpu-memory-utilization {sys.argv[1]}',
                    new_args
                )
                if '--gpu-memory-utilization' not in new_args:
                    # Add it before the final newline
                    new_args = new_args.rstrip() + f' \\\n              --gpu-memory-utilization {sys.argv[1]}'
                container['args'] = [new_args]
            break

with open('/tmp/first-deployment-updated.yaml', 'w') as f:
    yaml.dump(deploy, f)
EOF
${MEMORY_UTIL}

# Apply updated deployment
kubectl apply -f /tmp/first-deployment-updated.yaml

# Restart the deployment
kubectl rollout restart deployment/vllm-model-deployment -n ${NAMESPACE}

echo "✅ Updated first instance to use ${MEMORY_UTIL} GPU memory"
echo "Waiting for rollout..."
kubectl rollout status deployment/vllm-model-deployment -n ${NAMESPACE} --timeout=300s

