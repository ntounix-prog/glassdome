# Glassdome Reaper Container
# ===========================
# Vulnerability injection worker

FROM python:3.12-slim

LABEL maintainer="Glassdome Team"
LABEL description="Glassdome Reaper - Vulnerability Injection Agent"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Network tools
    iproute2 \
    iputils-ping \
    vlan \
    # SSH for VM access
    openssh-client \
    sshpass \
    # Exploitation tools
    nmap \
    netcat-openbsd \
    # Build tools
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

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
ENV GLASSDOME_MODE=reaper

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD celery -A glassdome.workers.reaper inspect ping -d ${WORKER_ID}@$HOSTNAME || exit 1

ENTRYPOINT ["./entrypoint.sh"]

