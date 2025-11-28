"""
Celery worker for celery_app

Author: Brett Turner (ntounix-prog)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import os
from celery import Celery

# Redis URL from environment or default
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "glassdome",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "glassdome.workers.orchestrator",
        "glassdome.workers.reaper",
        "glassdome.workers.whiteknight",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # Soft limit at 55 mins
    
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_concurrency=4,
    
    # Result backend
    result_expires=86400,  # Results expire after 24 hours
    
    # Task queues
    task_queues={
        "deploy": {"exchange": "deploy", "routing_key": "deploy"},
        "configure": {"exchange": "configure", "routing_key": "configure"},
        "network": {"exchange": "network", "routing_key": "network"},
        "inject": {"exchange": "inject", "routing_key": "inject"},
        "exploit": {"exchange": "exploit", "routing_key": "exploit"},
        "validate": {"exchange": "validate", "routing_key": "validate"},
        "test": {"exchange": "test", "routing_key": "test"},
        "monitor": {"exchange": "monitor", "routing_key": "monitor"},
    },
    
    # Task routes
    task_routes={
        "glassdome.workers.orchestrator.*": {"queue": "deploy"},
        "glassdome.workers.reaper.*": {"queue": "inject"},
        "glassdome.workers.whiteknight.*": {"queue": "validate"},
    },
)

