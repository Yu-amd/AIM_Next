FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy controller code
COPY finetuning_controller.py .

# Run controller
CMD ["python3", "finetuning_controller.py"]

