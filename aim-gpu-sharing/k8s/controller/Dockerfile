FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY k8s/controller/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy controller code
COPY k8s/controller/ /app/
COPY runtime/ /app/runtime/

# Set Python path
ENV PYTHONPATH=/app:/app/runtime

# Run controller
CMD ["python3", "main.py"]

