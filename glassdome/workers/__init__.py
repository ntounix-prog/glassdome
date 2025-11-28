"""
Celery worker for __init__

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

from .celery_app import celery_app

__all__ = ["celery_app"]

