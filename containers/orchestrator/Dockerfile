# Glassdome Orchestrator Container
# =================================
# Base image for all Glassdome workers
# Handles: Lab deployment, VM provisioning, network configuration

FROM python:3.12-slim

LABEL maintainer="Glassdome Team"
LABEL description="Glassdome Orchestrator - Lab Deployment Engine"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Network tools for VLAN attachment
    iproute2 \
    iputils-ping \
    bridge-utils \
    vlan \
    # SSH for VM configuration
    openssh-client \
    sshpass \
    # Build tools
    gcc \
    libffi-dev \
    # Utilities
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional container-specific dependencies
RUN pip install --no-cache-dir \
    celery[redis] \
    redis \
    aioredis

# Copy application code
COPY glassdome/ ./glassdome/
COPY containers/orchestrator/entrypoint.sh .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Create log directory
RUN mkdir -p /app/logs

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV GLASSDOME_MODE=orchestrator
ENV REDIS_URL=redis://localhost:6379/0
ENV WORKER_CONCURRENCY=4

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import redis; r=redis.from_url('$REDIS_URL'); r.ping()" || exit 1

# Entrypoint handles mode switching (backend vs worker)
ENTRYPOINT ["./entrypoint.sh"]

