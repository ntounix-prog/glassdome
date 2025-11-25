#!/bin/bash
# Fix mxwest Postfix TLS configuration to work with mooker
# This script configures mxwest to skip certificate verification for mail.xisx.org

set -e

echo "=== Fixing mxwest Postfix TLS Configuration ==="
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo"
    exit 1
fi

POSTFIX_DIR="/etc/postfix"
TLS_POLICY_FILE="$POSTFIX_DIR/tls_policy"

echo "1. Updating TLS policy map..."
# Check if tls_policy file exists and update it
if [ -f "$TLS_POLICY_FILE" ]; then
    # Update existing entry for mail.xisx.org to 'encrypt' (require TLS)
    if grep -q "^mail.xisx.org" "$TLS_POLICY_FILE"; then
        echo "   Updating existing mail.xisx.org entry to 'encrypt'"
        sed -i 's|^mail.xisx.org.*|mail.xisx.org encrypt|' "$TLS_POLICY_FILE"
    else
        echo "   Adding mail.xisx.org entry"
        echo "mail.xisx.org encrypt" >> "$TLS_POLICY_FILE"
    fi
else
    echo "   Creating new TLS policy file"
    cat > "$TLS_POLICY_FILE" <<EOF
# TLS policy for mail.xisx.org (mooker)
# 'encrypt' requires TLS but we'll disable cert verification globally
mail.xisx.org encrypt
EOF
fi

echo "2. Creating TLS policy hash database..."
postmap "$TLS_POLICY_FILE"

echo "3. Updating Postfix main.cf..."
# Check if smtp_tls_policy_maps is already set
if grep -q "^smtp_tls_policy_maps" "$POSTFIX_DIR/main.cf"; then
    echo "   smtp_tls_policy_maps already configured"
    # Check if our policy file is already in the list
    if grep "^smtp_tls_policy_maps" "$POSTFIX_DIR/main.cf" | grep -q "hash:$TLS_POLICY_FILE"; then
        echo "   ✓ TLS policy file already in configuration"
    else
        echo "   Adding our TLS policy to existing configuration..."
        # Append to existing policy maps (comma-separated)
        sed -i "s|^smtp_tls_policy_maps = \(.*\)|smtp_tls_policy_maps = \1, hash:$TLS_POLICY_FILE|" "$POSTFIX_DIR/main.cf"
    fi
else
    echo "   Adding smtp_tls_policy_maps..."
    echo "smtp_tls_policy_maps = hash:$TLS_POLICY_FILE" >> "$POSTFIX_DIR/main.cf"
fi

# Also disable certificate verification for mail.xisx.org
# This allows TLS to work even if certificate doesn't match perfectly
echo "4. Configuring certificate verification..."
if ! grep -q "^smtp_tls_verify_cert_match" "$POSTFIX_DIR/main.cf"; then
    echo "   Setting smtp_tls_verify_cert_match = none (skip cert verification)"
    echo "smtp_tls_verify_cert_match = none" >> "$POSTFIX_DIR/main.cf"
else
    echo "   smtp_tls_verify_cert_match already configured"
fi

# Also ensure we're using mail.xisx.org in transport map (already done, but verify)
echo "5. Verifying transport map uses mail.xisx.org..."
if [ -f "$POSTFIX_DIR/transport" ]; then
    if grep -q "mail.xisx.org" "$POSTFIX_DIR/transport"; then
        echo "   ✓ Transport map already uses mail.xisx.org"
    else
        echo "   ⚠️  Transport map may need updating - check manually"
    fi
fi

echo "6. Reloading Postfix..."
postfix reload

echo ""
echo "=== Configuration Complete ==="
echo ""
echo "TLS policy configured:"
echo "  mail.xisx.org -> encrypt (require TLS)"
echo "  Certificate verification disabled globally (smtp_tls_verify_cert_match = none)"
echo ""
echo "To verify, check:"
echo "  postconf smtp_tls_policy_maps"
echo "  postmap -q mail.xisx.org $TLS_POLICY_FILE"
echo ""
echo "Now try: sudo postqueue -f"

