#!/bin/bash
# Import Docker image to containerd with progress

set -e

echo "=== Importing aim-finetuning image to containerd ==="
echo ""

# Step 1: Save to file (shows progress)
echo "Step 1: Saving Docker image to file..."
docker save aim-finetuning:latest -o /tmp/aim-finetuning.tar
echo "✓ Image saved to /tmp/aim-finetuning.tar"
echo ""

# Step 2: Import to containerd
echo "Step 2: Importing to containerd..."
sudo ctr -n k8s.io images import /tmp/aim-finetuning.tar
echo "✓ Image imported to containerd"
echo ""

# Step 3: Verify
echo "Step 3: Verifying import..."
sudo ctr -n k8s.io images list | grep aim-finetuning && echo "✓ Image found in containerd" || echo "✗ Image not found"

# Cleanup
echo ""
echo "Cleaning up temporary file..."
rm -f /tmp/aim-finetuning.tar
echo "✓ Done!"
