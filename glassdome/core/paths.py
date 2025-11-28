"""
Paths module

Author: Brett Turner (ntounix-prog)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
from pathlib import Path
import os

# =============================================================================
# PROJECT ROOT
# =============================================================================
# Derived from this file's location: glassdome/core/paths.py -> glassdome/
# Going up: paths.py -> core/ -> glassdome/ -> project_root/

_DEFAULT_ROOT = Path(__file__).resolve().parent.parent.parent

# Allow override via environment variable for special deployments
PROJECT_ROOT = Path(os.environ.get("GLASSDOME_ROOT", _DEFAULT_ROOT))

# =============================================================================
# DATA DIRECTORY
# =============================================================================
# Where runtime data is stored (secrets, logs, state files)
# Can be separate from project root in containerized/multi-user deployments

GLASSDOME_DATA_DIR = Path(os.environ.get("GLASSDOME_DATA_DIR", PROJECT_ROOT))

# =============================================================================
# SECRETS & SESSION
# =============================================================================
# All secrets-related files go in .secrets/ subdirectory
SECRETS_DIR = GLASSDOME_DATA_DIR / ".secrets"

# Master key (encrypted with user password)
MASTER_KEY_PATH = SECRETS_DIR / "master_key.enc"

# Encrypted secrets store
SECRETS_STORE_PATH = SECRETS_DIR / "secrets.encrypted"

# Registry of known secret keys (for listing without decrypting)
SECRETS_REGISTRY_PATH = SECRETS_DIR / "secrets_registry.json"

# Human-readable secret names mapping
SECRET_NAMES_PATH = SECRETS_DIR / "secret_names.json"

# Session cache (metadata only, no secrets)
SESSION_CACHE_PATH = SECRETS_DIR / "session_cache.json"

# Session key for cross-process master key sharing (protected 0600)
SESSION_KEY_PATH = SECRETS_DIR / "session_key.bin"

# =============================================================================
# LOGS
# =============================================================================
LOGS_DIR = GLASSDOME_DATA_DIR / "logs"

# Specific log files
REAPER_LOG = LOGS_DIR / "reaper.log"
API_LOG = LOGS_DIR / "api.log"

# =============================================================================
# APPLICATION STATE
# =============================================================================
# RAG knowledge index
RAG_INDEX_DIR = GLASSDOME_DATA_DIR / ".rag_index"

# Overseer state (VMs, missions, etc.)
OVERSEER_STATE_FILE = GLASSDOME_DATA_DIR / ".overseer_state.json"

# =============================================================================
# CONFIGURATION
# =============================================================================
# Config directory (templates, IP pools, etc.)
CONFIG_DIR = PROJECT_ROOT / "config"

# Environment file
ENV_FILE = GLASSDOME_DATA_DIR / ".env"

# IP pools configuration
IP_POOLS_FILE = CONFIG_DIR / "ip_pools.json"

# =============================================================================
# DOCUMENTATION & ASSETS
# =============================================================================
DOCS_DIR = PROJECT_ROOT / "docs"
SESSION_LOGS_DIR = DOCS_DIR / "session_logs"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def ensure_directories() -> None:
    """Ensure all required directories exist with proper permissions."""
    # Create directories
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Set restrictive permissions on secrets directory
    try:
        os.chmod(SECRETS_DIR, 0o700)
    except OSError:
        pass  # May fail on some filesystems


def get_relative_path(absolute_path: Path) -> Path:
    """Convert absolute path to relative path from project root."""
    try:
        return absolute_path.relative_to(PROJECT_ROOT)
    except ValueError:
        return absolute_path


def resolve_path(path_str: str) -> Path:
    """
    Resolve a path string to an absolute path.
    
    - If absolute, returns as-is
    - If relative, resolves from PROJECT_ROOT
    """
    path = Path(path_str)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


# =============================================================================
# DEBUG INFO
# =============================================================================

def print_paths() -> None:
    """Print all configured paths for debugging."""
    print("=" * 60)
    print("GLASSDOME PATH CONFIGURATION")
    print("=" * 60)
    print(f"PROJECT_ROOT:        {PROJECT_ROOT}")
    print(f"GLASSDOME_DATA_DIR:  {GLASSDOME_DATA_DIR}")
    print(f"SECRETS_DIR:         {SECRETS_DIR}")
    print(f"LOGS_DIR:            {LOGS_DIR}")
    print(f"RAG_INDEX_DIR:       {RAG_INDEX_DIR}")
    print(f"ENV_FILE:            {ENV_FILE}")
    print("=" * 60)


# Ensure directories exist on import
ensure_directories()

