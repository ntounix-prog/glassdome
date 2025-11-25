#!/bin/bash
# Monitor mooker TLS connections and log detailed TLS handshake information
# Run this while triggering mail queue on mxwest

MOOKER_HOST="192.168.3.69"
MOOKER_USER="nomad"
SSH_KEY="$HOME/.ssh/mooker_key"

echo "Monitoring mooker Postfix TLS connections..."
echo "Press Ctrl+C to stop"
echo ""

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$MOOKER_USER@$MOOKER_HOST" \
  "docker logs mailcowdockerized-postfix-mailcow-1 -f 2>&1" | \
  grep --line-buffered -E '10.30.0.1|TLS|SSL|STARTTLS|timeout|SSL_accept|handshake|ECDH|cipher|protocol'

