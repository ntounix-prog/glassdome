#!/bin/bash
# Fix WireGuard MTU to resolve TLS handshake timeouts
# Run on both mxwest and Rome

set -e

MTU=1400

echo "=== Fixing WireGuard MTU ==="
echo "Setting MTU to $MTU to match path MTU"
echo ""

# Check if WireGuard config exists
if [ ! -f /etc/wireguard/wg0.conf ]; then
    echo "Error: /etc/wireguard/wg0.conf not found"
    exit 1
fi

# Backup config
cp /etc/wireguard/wg0.conf /etc/wireguard/wg0.conf.backup.$(date +%Y%m%d_%H%M%S)

# Add or update MTU in config
if grep -q "^MTU" /etc/wireguard/wg0.conf; then
    echo "Updating existing MTU setting..."
    sed -i "s/^MTU.*/MTU = $MTU/" /etc/wireguard/wg0.conf
else
    echo "Adding MTU setting to [Interface] section..."
    # Add MTU after Address line in [Interface] section
    sed -i "/^\[Interface\]/,/^\[/ { /^Address/a MTU = $MTU" -e '}' /etc/wireguard/wg0.conf
    # If that didn't work, add it after the first non-comment line in [Interface]
    if ! grep -q "^MTU" /etc/wireguard/wg0.conf; then
        sed -i "/^\[Interface\]/a MTU = $MTU" /etc/wireguard/wg0.conf
    fi
fi

echo ""
echo "Updated config:"
grep -A 5 "^\[Interface\]" /etc/wireguard/wg0.conf | head -6

echo ""
echo "Restarting WireGuard..."
if systemctl is-active --quiet wg-quick@wg0; then
    systemctl restart wg-quick@wg0
else
    wg-quick down wg0 2>/dev/null || true
    wg-quick up wg0
fi

sleep 2

echo ""
echo "Verifying MTU:"
ip addr show wg0 | grep mtu

echo ""
echo "✅ WireGuard MTU updated to $MTU"
echo "Test TLS handshake now - it should work!"

