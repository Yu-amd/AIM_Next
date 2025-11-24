FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Presidio models
RUN python3 -c "from presidio_analyzer import AnalyzerEngine; AnalyzerEngine()" || true

# Copy application code
COPY guardrails/ ./guardrails/
COPY integration/ ./integration/

# Set Python path
ENV PYTHONPATH=/app

# Expose ports (8080 for API, 9090 for metrics)
EXPOSE 8080 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Run API server
CMD ["python3", "-m", "guardrails.api.server"]

