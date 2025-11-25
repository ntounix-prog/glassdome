#!/usr/bin/env python3
"""
Test platform connections using secrets-loaded Settings/Session.

This is a **non-destructive** connectivity test:
- Proxmox: version API
- ESXi: basic API info
- AWS: describe_regions
- Azure: list resource groups
- Mailcow: list mailboxes

All credentials are loaded via GlassdomeSession → Settings → SecretsManager.

Authentication model for this script:
- **Does NOT prompt** for the master password.
- Relies on an already-initialized session/cache, just like agents do.
- If the session/cache is not available, it fails with a clear message and
  asks you to run `./glassdome_start` first.
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


def _get_session_and_settings():
    """
    Initialize security context and return (session, settings), agent-style.
    
    IMPORTANT:
    - This function NEVER prompts for the master password.
    - It relies on cache + keyring only (same behavior agents experience).
    - If the session/cache is not available, it raises a clear error telling
      you to run `./glassdome_start` or use the auth API first.
    """
    from glassdome.core.security import ensure_security_context, get_secure_settings
    from glassdome.core.session import get_session

    # Use the same bootstrap helper agents/servers use
    ensure_security_context()
    session = get_session()
    settings = get_secure_settings()
    return session, settings


async def test_proxmox(settings):
    """Test Proxmox connection via ProxmoxFactory if configured."""
    print("\n" + "=" * 70)
    print("PROXMOX CONNECTION TEST")
    print("=" * 70)

    try:
        from glassdome.platforms.proxmox_factory import get_proxmox_client

        # get_proxmox_config will use secrets manager via Settings
        cfg = settings.get_proxmox_config("01")
        if not cfg.get("host"):
            print("⏭️  Skipping Proxmox (no host configured in Settings/secrets).")
            return None

        client = get_proxmox_client("01")
        ok = await client.test_connection()
        if ok:
            print(f"✅ Proxmox connection OK (host={cfg.get('host')}, user={cfg.get('user')})")
            return True
        else:
            print("❌ Proxmox connection FAILED")
            return False
    except Exception as e:
        print(f"❌ Proxmox test error: {e}")
        return False


async def test_esxi(settings):
    """Test ESXi connection if configured (host + password)."""
    print("\n" + "=" * 70)
    print("ESXi CONNECTION TEST")
    print("=" * 70)

    try:
        from glassdome.platforms.esxi_client import ESXiClient

        host = getattr(settings, "esxi_host", None)
        user = getattr(settings, "esxi_user", "root")
        password = getattr(settings, "esxi_password", None)
        datastore = getattr(settings, "esxi_datastore", None)
        network = getattr(settings, "esxi_network", "VM Network")

        if not host or not password:
            print("⏭️  Skipping ESXi (host/password not configured in Settings/secrets).")
            return None

        client = ESXiClient(
            host=host,
            user=user or "root",
            password=password,
            verify_ssl=False,
            datastore_name=datastore,
            network_name=network,
        )

        ok = await client.test_connection()
        if ok:
            print(f"✅ ESXi connection OK (host={host}, user={user or 'root'})")
            return True
        else:
            print("❌ ESXi connection FAILED")
            return False
    except Exception as e:
        print(f"❌ ESXi test error: {e}")
        return False


async def test_aws(settings):
    """Test AWS connection if credentials configured."""
    print("\n" + "=" * 70)
    print("AWS CONNECTION TEST")
    print("=" * 70)

    try:
        from glassdome.platforms.aws_client import AWSClient

        access_key = getattr(settings, "aws_access_key_id", None)
        secret_key = getattr(settings, "aws_secret_access_key", None)
        region = getattr(settings, "aws_region", "us-east-1")

        if not access_key or not secret_key:
            print("⏭️  Skipping AWS (access key/secret not configured in Settings/secrets).")
            return None

        client = AWSClient(
            access_key_id=access_key,
            secret_access_key=secret_key,
            region=region,
        )

        ok = await client.test_connection()
        if ok:
            print(f"✅ AWS connection OK (region={region})")
            return True
        else:
            print("❌ AWS connection FAILED")
            return False
    except Exception as e:
        print(f"❌ AWS test error: {e}")
        return False


async def test_azure(settings):
    """Test Azure connection if credentials configured."""
    print("\n" + "=" * 70)
    print("AZURE CONNECTION TEST")
    print("=" * 70)

    try:
        from glassdome.platforms.azure_client import AzureClient

        subscription_id = getattr(settings, "azure_subscription_id", None)
        tenant_id = getattr(settings, "azure_tenant_id", None)
        client_id = getattr(settings, "azure_client_id", None)
        client_secret = getattr(settings, "azure_client_secret", None)
        region = getattr(settings, "azure_region", "eastus")
        resource_group = getattr(settings, "azure_resource_group", None)

        if not (subscription_id and tenant_id and client_id and client_secret and resource_group):
            print("⏭️  Skipping Azure (one or more credentials missing in Settings/secrets).")
            return None

        client = AzureClient(
            subscription_id=subscription_id,
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            region=region,
            resource_group=resource_group,
        )

        ok = await client.test_connection()
        if ok:
            print(f"✅ Azure connection OK (region={region}, rg={resource_group})")
            return True
        else:
            print("❌ Azure connection FAILED")
            return False
    except Exception as e:
        print(f"❌ Azure test error: {e}")
        return False


async def test_mailcow(settings):
    """Test Mailcow API connection by listing mailboxes, if configured."""
    print("\n" + "=" * 70)
    print("MAILCOW CONNECTION TEST")
    print("=" * 70)

    try:
        from glassdome.integrations.mailcow_client import MailcowClient

        api_token = getattr(settings, "mail_api", None)
        api_url = getattr(settings, "mailcow_api_url", None)
        domain = getattr(settings, "mailcow_domain", "xisx.org")
        verify_ssl = getattr(settings, "mailcow_verify_ssl", False)

        if not api_token:
            print("⏭️  Skipping Mailcow (MAIL_API / mail_api not configured in Settings/secrets).")
            return None

        if not api_url:
            api_url = f"https://mail.{domain}"

        client = MailcowClient(
            api_url=api_url,
            api_token=api_token,
            domain=domain,
            imap_host=getattr(settings, "mailcow_imap_host", None),
            smtp_host=getattr(settings, "mailcow_smtp_host", None),
            verify_ssl=verify_ssl,
        )

        result = client.list_mailboxes()
        if result.get("success"):
            print(f"✅ Mailcow API OK (domain={domain}, mailboxes={result.get('count', 0)})")
            return True
        else:
            print(f"❌ Mailcow API FAILED: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Mailcow test error: {e}")
        return False


async def main():
    print("\n" + "=" * 70)
    print("GLASSDOME PLATFORM CONNECTION TESTS")
    print("=" * 70)

    _, settings = _get_session_and_settings()

    results = {}
    results["proxmox"] = await test_proxmox(settings)
    results["esxi"] = await test_esxi(settings)
    results["aws"] = await test_aws(settings)
    results["azure"] = await test_azure(settings)
    results["mailcow"] = await test_mailcow(settings)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for name, ok in results.items():
        if ok is True:
            status = "✅ OK"
        elif ok is False:
            status = "❌ FAIL"
        else:
            status = "⏭️  SKIP"
        print(f"{status:10s} - {name}")

    print("\nNote: SKIP means that platform credentials are not configured "
          "in Settings/secrets; this is expected if you don't use that platform.")

    # Exit code: 0 if nothing failed (ignoring skips)
    failures = [k for k, v in results.items() if v is False]
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))


