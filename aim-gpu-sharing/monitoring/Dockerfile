FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY monitoring/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy metrics exporter code
COPY monitoring/ /app/
COPY runtime/ /app/runtime/

# Set Python path
ENV PYTHONPATH=/app:/app/runtime

# Expose metrics port
EXPOSE 8080

# Run metrics exporter
CMD ["python3", "metrics_exporter.py"]

