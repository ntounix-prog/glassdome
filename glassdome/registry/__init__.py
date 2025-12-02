"""
Glassdome Registry Module

Manages the central registry of all deployed resources across platforms.
Uses Redis as the source of truth with periodic reconciliation.

Author: Brett Turner (ntounix)
Created: December 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

from glassdome.registry.reconciler import (
    RegistryReconciler,
    get_reconciler,
    start_reconciler,
    force_reconcile,
    Resource,
    ResourceType,
    ProxmoxScanner,
    AWSScanner,
)

__all__ = [
    "RegistryReconciler",
    "get_reconciler", 
    "start_reconciler",
    "force_reconcile",
    "Resource",
    "ResourceType",
    "ProxmoxScanner",
    "AWSScanner",
]
