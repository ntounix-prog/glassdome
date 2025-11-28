"""
Celery worker for __init__

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""

from .celery_app import celery_app

__all__ = ["celery_app"]

