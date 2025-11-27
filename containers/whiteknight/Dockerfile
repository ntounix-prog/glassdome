# Glassdome WhiteKnight Container
# =================================
# Vulnerability validation worker

FROM python:3.12-slim

LABEL maintainer="Glassdome Team"
LABEL description="Glassdome WhiteKnight - Vulnerability Validation Agent"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Network tools
    iproute2 \
    iputils-ping \
    vlan \
    # SSH
    openssh-client \
    sshpass \
    # Security testing tools
    nmap \
    netcat-openbsd \
    curl \
    git \
    # Build tools
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install security tools via pip
RUN pip install --no-cache-dir sqlmap

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir celery[redis] redis asyncssh

COPY glassdome/ ./glassdome/
COPY containers/orchestrator/entrypoint.sh .

RUN chmod +x entrypoint.sh
RUN mkdir -p /app/logs

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV GLASSDOME_MODE=whiteknight

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD celery -A glassdome.workers.whiteknight inspect ping -d ${WORKER_ID}@$HOSTNAME || exit 1

ENTRYPOINT ["./entrypoint.sh"]

