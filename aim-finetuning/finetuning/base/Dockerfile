FROM rocm/rocm-terminal:latest

# Install Python dependencies
RUN pip3 install --no-cache-dir \
    torch>=2.0.0 \
    transformers>=4.35.0 \
    peft>=0.6.0 \
    datasets>=2.14.0 \
    accelerate>=0.24.0 \
    sentencepiece>=0.1.99 \
    protobuf>=3.20.0

# Set working directory
WORKDIR /workspace

# Copy fine-tuning code
COPY finetuning/ /workspace/finetuning/
COPY requirements.txt /workspace/

# Copy example templates (including example dataset)
COPY templates/ /workspace/templates/

# Install local package
RUN pip3 install -e /workspace || pip3 install -r /workspace/requirements.txt

# Set Python path
ENV PYTHONPATH=/workspace:$PYTHONPATH

# Default command
ENTRYPOINT ["python3", "-m", "finetuning.base.app"]

