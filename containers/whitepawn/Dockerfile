# Glassdome WhitePawn Container
# ===============================
# Continuous network monitoring

FROM python:3.12-slim

LABEL maintainer="Glassdome Team"
LABEL description="Glassdome WhitePawn - Continuous Network Monitor"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Network tools
    iproute2 \
    iputils-ping \
    vlan \
    traceroute \
    tcpdump \
    iperf3 \
    # Utilities
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir redis aioredis

COPY glassdome/ ./glassdome/
COPY containers/orchestrator/entrypoint.sh .

RUN chmod +x entrypoint.sh
RUN mkdir -p /app/logs

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV GLASSDOME_MODE=whitepawn
ENV MONITOR_INTERVAL=15

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import redis; r=redis.from_url('$REDIS_URL'); r.ping()" || exit 1

ENTRYPOINT ["./entrypoint.sh"]

