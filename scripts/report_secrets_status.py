#!/usr/bin/env python3
"""
Report status of all important secrets across:
- Secure store (SecretsManager)
- Environment variables
- .env
- .env-org (backup)
- ~/.bashrc

This helps during the transition to ensure we don't lose any credentials
and can re-enter missing ones via the secrets web UI or CLI.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List


PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


def load_env_file(path: Path) -> Dict[str, str]:
    """Minimal .env parser (KEY=VALUE, ignores comments)."""
    result: Dict[str, str] = {}
    if not path.exists():
        return result
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                result[key] = value
    except Exception:
        # Fail soft; this is just a diagnostic helper
        pass
    return result


def load_bashrc_exports(path: Path) -> Dict[str, str]:
    """Parse export KEY=VALUE lines from ~/.bashrc."""
    result: Dict[str, str] = {}
    if not path.exists():
        return result
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if not line.startswith("export ") or "=" not in line:
                    continue
                line = line[len("export ") :].strip()
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                result[key] = value
    except Exception:
        pass
    return result


def main() -> int:
    from glassdome.core.secrets import get_secrets_manager

    print("\n" + "=" * 70)
    print("GLASSDOME SECRETS STATUS REPORT")
    print("=" * 70)

    # Canonical secret keys and their legacy environment names
    canonical_secrets: Dict[str, List[str]] = {
        # AI / LLM
        "openai_api_key": ["OPENAI_API_KEY"],
        "anthropic_api_key": ["ANTHROPIC_API_KEY"],
        "xai_api_key": ["XAI_API_KEY"],
        "perplexity_api_key": ["PERPLEXITY_API_KEY"],
        "rapidapi_key": ["RAPIDAPI_KEY"],
        "google_search_api_key": ["GOOGLE_SEARCH_API_KEY", "GOOGLE_SEARCH_API"],
        "google_engine_id": ["GOOGLE_ENGINE_ID"],
        # Proxmox
        "proxmox_password": ["PROXMOX_PASSWORD", "PROXMOX_ADMIN_PASSWD"],
        "proxmox_token_value": ["PROXMOX_TOKEN_VALUE"],
        "proxmox_token_value_02": ["PROXMOX_TOKEN_VALUE_02"],
        "proxmox_root_password": ["PROXMOX_ROOT_PASSWORD"],
        # ESXi
        "esxi_password": ["ESXI_PASSWORD"],
        # Azure
        "azure_client_secret": ["AZURE_CLIENT_SECRET"],
        # AWS
        "aws_secret_access_key": ["AWS_SECRET_ACCESS_KEY"],
        # Mailcow
        "mail_api": ["MAIL_API"],
        # Core app
        "secret_key": ["SECRET_KEY"],
    }

    sm = get_secrets_manager()
    stored = set(sm.list_secrets())

    env = dict(os.environ)
    env_path = PROJECT_ROOT / ".env"
    env_org_path = PROJECT_ROOT / ".env-org"
    bashrc_path = Path.home() / ".bashrc"

    env_file = load_env_file(env_path)
    env_org_file = load_env_file(env_org_path)
    bashrc_exports = load_bashrc_exports(bashrc_path)

    rows = []
    for canon_key, legacy_env_names in canonical_secrets.items():
        in_store = canon_key in stored

        # Look for any value for this secret in env/.env/.env-org/.bashrc
        sources = []
        sample_value = None

        # Check environment variables
        for name in legacy_env_names:
            if name in env and env[name]:
                sources.append(f"ENV:{name}")
                if sample_value is None:
                    sample_value = env[name]

        # Check .env
        for name in legacy_env_names:
            if name in env_file and env_file[name]:
                sources.append(f".env:{name}")
                if sample_value is None:
                    sample_value = env_file[name]

        # Check .env-org
        for name in legacy_env_names:
            if name in env_org_file and env_org_file[name]:
                sources.append(f".env-org:{name}")
                if sample_value is None:
                    sample_value = env_org_file[name]

        # Check ~/.bashrc
        for name in legacy_env_names:
            if name in bashrc_exports and bashrc_exports[name]:
                sources.append(f".bashrc:{name}")
                if sample_value is None:
                    sample_value = bashrc_exports[name]

        has_source = bool(sources)

        rows.append(
            {
                "key": canon_key,
                "stored": in_store,
                "has_source": has_source,
                "sources": ", ".join(sources) if sources else "",
                "example": (sample_value[:24] + "...") if sample_value else "",
            }
        )

    # Print report
    print(f"{'Secret Key':30s} | {'In Store':8s} | {'Has Source':10s} | Sources")
    print("-" * 70)
    for row in rows:
        print(
            f"{row['key']:30s} | "
            f"{str(row['stored']):8s} | "
            f"{str(row['has_source']):10s} | "
            f"{row['sources']}"
        )

    print("\nDetails:")
    for row in rows:
        if not row["stored"] and row["has_source"]:
            print(
                f"- {row['key']}: NOT in secrets store, but found in {row['sources']} "
                f"(example: {row['example']})"
            )
        elif not row["stored"] and not row["has_source"]:
            print(
                f"- {row['key']}: MISSING everywhere (no secret in store, env, .env, .env-org, or .bashrc)"
            )

    print(
        "\nNext steps:\n"
        "- For any key with Has Source=True and In Store=False:\n"
        "    → Use the secrets web UI or `glassdome secrets set` to add it\n"
        "- For any key with Has Source=False and In Store=False:\n"
        "    → You will need to re-enter it manually from the upstream platform\n"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())


