#!/bin/bash
# Test TLS connection from mxwest to mooker
# Run this on mxwest after applying TLS fixes

set -e

MOOKER_HOST="mail.xisx.org"
MOOKER_IP="192.168.3.69"

echo "=== Testing TLS Connection to Mooker ==="
echo ""

echo "1. Testing connection by hostname (mail.xisx.org)..."
if timeout 10 openssl s_client -connect "$MOOKER_HOST:25" -starttls smtp -servername "$MOOKER_HOST" 2>&1 | grep -q "Verify return code: 0"; then
    echo "   ✅ TLS connection by hostname: SUCCESS"
else
    echo "   ❌ TLS connection by hostname: FAILED"
fi

echo ""
echo "2. Testing connection by IP (192.168.3.69)..."
if timeout 10 openssl s_client -connect "$MOOKER_IP:25" -starttls smtp -servername "$MOOKER_HOST" 2>&1 | grep -q "Verify return code: 0"; then
    echo "   ✅ TLS connection by IP: SUCCESS"
else
    echo "   ⚠️  TLS connection by IP: Certificate verification will fail (expected)"
    echo "      This is why we need to skip verification in Postfix"
fi

echo ""
echo "3. Testing Postfix connection..."
if timeout 10 telnet "$MOOKER_HOST" 25 <<EOF | grep -q "220"
EHLO test
QUIT
EOF
then
    echo "   ✅ SMTP connection: SUCCESS"
else
    echo "   ❌ SMTP connection: FAILED"
fi

echo ""
echo "4. Checking mail queue..."
if sudo postqueue -p | grep -q "Mail queue is empty"; then
    echo "   ✅ Mail queue: EMPTY"
else
    echo "   ⚠️  Mail queue: HAS MESSAGES"
    echo "      Run: sudo postqueue -f"
fi

echo ""
echo "=== Test Complete ==="

