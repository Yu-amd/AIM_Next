#!/bin/bash

# Script to validate Prometheus metrics are accessible via SSH port forwarding

METRICS_PORT=${1:-8000}
METRICS_URL="http://localhost:${METRICS_PORT}/metrics"

echo "=== Validating Metrics Access via SSH Port Forwarding ==="
echo ""
echo "Metrics URL: $METRICS_URL"
echo ""

# 1. Check if port is listening locally
echo "1. Checking if port $METRICS_PORT is listening locally..."
if netstat -tlnp 2>/dev/null | grep -q ":$METRICS_PORT " || \
   ss -tlnp 2>/dev/null | grep -q ":$METRICS_PORT " || \
   lsof -i :$METRICS_PORT 2>/dev/null | grep -q LISTEN; then
    echo "   ✓ Port $METRICS_PORT is listening"
else
    echo "   ✗ Port $METRICS_PORT is NOT listening"
    echo "   → Make sure SSH port forwarding is active:"
    echo "     ssh -L ${METRICS_PORT}:localhost:${METRICS_PORT} user@remote-server"
    exit 1
fi

echo ""

# 2. Test basic connectivity
echo "2. Testing connectivity to metrics endpoint..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$METRICS_URL" 2>/dev/null)

if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✓ Metrics endpoint is accessible (HTTP $HTTP_CODE)"
else
    echo "   ✗ Metrics endpoint returned HTTP $HTTP_CODE"
    echo "   → Check if metrics server is running on remote host"
    exit 1
fi

echo ""

# 3. Check for fine-tuning metrics
echo "3. Checking for fine-tuning metrics..."
METRICS_COUNT=$(curl -s "$METRICS_URL" 2>/dev/null | grep -c "finetuning" || echo "0")

if [ "$METRICS_COUNT" -gt 0 ]; then
    echo "   ✓ Found $METRICS_COUNT fine-tuning metrics"
else
    echo "   ⚠ No fine-tuning metrics found (metrics server may not be running or no jobs active)"
    echo "   → Start training with --enable-metrics flag"
fi

echo ""

# 4. Display sample metrics
echo "4. Sample fine-tuning metrics:"
echo ""
curl -s "$METRICS_URL" 2>/dev/null | grep "finetuning" | head -10
if [ $? -ne 0 ]; then
    echo "   (No fine-tuning metrics available)"
fi

echo ""
echo ""

# 5. Check specific metrics
echo "5. Checking specific metric types:"
echo ""

check_metric() {
    local metric_name=$1
    local count=$(curl -s "$METRICS_URL" 2>/dev/null | grep -c "^${metric_name}" || echo "0")
    if [ "$count" -gt 0 ]; then
        echo "   ✓ $metric_name: $count metric(s)"
    else
        echo "   - $metric_name: not found"
    fi
}

check_metric "finetuning_job_status"
check_metric "finetuning_train_loss"
check_metric "finetuning_training_progress"
check_metric "finetuning_gpu_utilization_percent"
check_metric "finetuning_checkpoints_total"

echo ""
echo ""

# 6. Summary
echo "=== Validation Summary ==="
echo ""

if [ "$HTTP_CODE" = "200" ] && [ "$METRICS_COUNT" -gt 0 ]; then
    echo "✅ SUCCESS: Metrics are accessible and contain fine-tuning data"
    echo ""
    echo "You can now:"
    echo "  - View metrics in browser: $METRICS_URL"
    echo "  - Scrape with Prometheus: target localhost:$METRICS_PORT"
    echo "  - Monitor in real-time: watch -n 5 'curl -s $METRICS_URL | grep finetuning'"
    exit 0
elif [ "$HTTP_CODE" = "200" ]; then
    echo "⚠ PARTIAL: Metrics endpoint is accessible but no fine-tuning metrics yet"
    echo ""
    echo "Next steps:"
    echo "  - Start a training job with --enable-metrics flag"
    echo "  - Wait for training to begin"
    echo "  - Run this script again to verify metrics appear"
    exit 0
else
    echo "❌ FAILED: Cannot access metrics endpoint"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Verify SSH port forwarding is active:"
    echo "     ps aux | grep 'ssh.*-L.*$METRICS_PORT'"
    echo ""
    echo "  2. Check if metrics server is running on remote:"
    echo "     ssh user@remote-server 'curl http://localhost:$METRICS_PORT/metrics'"
    echo ""
    echo "  3. Re-establish SSH tunnel:"
    echo "     ssh -L ${METRICS_PORT}:localhost:${METRICS_PORT} user@remote-server"
    exit 1
fi

