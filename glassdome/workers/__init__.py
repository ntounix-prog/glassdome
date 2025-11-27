"""
Glassdome Distributed Workers
=============================

Container-based workers for parallel lab deployment, vulnerability injection,
validation, and network monitoring.

Workers communicate via Redis and can attach to lab VLANs dynamically.
"""

from .celery_app import celery_app

__all__ = ["celery_app"]

