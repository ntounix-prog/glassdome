# WhiteKnight - Automated Vulnerability Validation Container
# Light version - fast builds, core tools only

FROM ubuntu:22.04

LABEL maintainer="Glassdome Team"
LABEL description="WhiteKnight - Automated vulnerability validation agent"
LABEL version="1.0"

ENV DEBIAN_FRONTEND=noninteractive

# ============================================================================
# CORE TOOLS - Essential for validation
# ============================================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    # SSH/Remote Access
    sshpass \
    openssh-client \
    # Web Testing
    curl \
    wget \
    # Network Tools
    nmap \
    netcat-openbsd \
    smbclient \
    iputils-ping \
    dnsutils \
    # Python
    python3 \
    python3-pip \
    # Utilities
    jq \
    ca-certificates \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# ADDITIONAL SECURITY TOOLS
# ============================================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Password/Brute Force
    hydra \
    # SNMP
    snmp \
    snmp-mibs-downloader \
    # MySQL/Postgres clients
    mysql-client \
    postgresql-client \
    # Redis
    redis-tools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# PYTHON SECURITY TOOLS
# ============================================================================
RUN pip3 install --no-cache-dir \
    requests \
    pyyaml \
    paramiko \
    python-nmap \
    impacket

# ============================================================================
# WHITEKNIGHT AGENT
# ============================================================================
WORKDIR /whiteknight

COPY agent/ /whiteknight/agent/
COPY requirements.txt /whiteknight/

ENTRYPOINT ["python3", "/whiteknight/agent/main.py"]

# ============================================================================
# USAGE
# ============================================================================
# Build:
#   docker build -t whiteknight:latest .
#
# Run credential test:
#   docker run --rm --network host whiteknight \
#     --target 192.168.3.100 --type CREDENTIAL \
#     --username user --password password123
#
# Run with JSON config:
#   docker run --rm --network host whiteknight \
#     --target 192.168.3.100 \
#     --config '{"exploit_type":"WEB","tags":["sqli"]}'
#
# Interactive shell:
#   docker run --rm -it --network host --entrypoint /bin/bash whiteknight
