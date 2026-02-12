# Build stage - install Python dependencies
FROM public.ecr.aws/docker/library/python:3.13.7-slim AS builder

WORKDIR /app

# Upgrade pip to fix CVE-2025-8869
RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .

# Install only from pre-built binary wheels to avoid Rust compilation timeouts
# If this fails, we need to either find wheels or use an older Python version
RUN pip install --no-cache-dir --only-binary :all: --target=/app/deps -r requirements.txt

# Runtime stage
FROM public.ecr.aws/docker/library/python:3.13.7-slim

# Apply security patches to base image packages and pip (CVE-2025-15467, CVE-2025-8869)
RUN apt-get update && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /app/deps /app/deps

# Copy application code
COPY src/ ./src/

ENV PYTHONPATH=/app/deps:/app/src

# stdio-based MCP server - no ports exposed
ENTRYPOINT ["python", "-u", "src/awx_mcp_server.py"]
