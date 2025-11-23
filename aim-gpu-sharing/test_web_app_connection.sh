#!/bin/bash
echo "Testing web app to vLLM connection..."

# Test vLLM endpoint
echo ""
echo "1. Testing vLLM endpoint (http://localhost:8002/v1/models):"
curl -s http://localhost:8002/v1/models | python3 -m json.tool 2>/dev/null | head -5 || echo "  ❌ vLLM endpoint not accessible"

# Test web app endpoint
echo ""
echo "2. Testing web app endpoint (http://localhost:5000/api/health):"
curl -s http://localhost:5000/api/health | python3 -m json.tool 2>/dev/null || echo "  ❌ Web app not responding"

# Test web app to vLLM
echo ""
echo "3. Testing web app API (http://localhost:5000/api/models):"
curl -s http://localhost:5000/api/models | python3 -m json.tool 2>/dev/null | head -5 || echo "  ❌ Web app API not working"
