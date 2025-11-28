"""
Worker Logging Configuration
============================

Structured logging for container workers.
All logs go to stdout (for Docker) AND to files (for debugging).
"""

import logging
import logging.handlers
import os
import json
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "worker_id": os.getenv("WORKER_ID", "unknown"),
            "worker_type": os.getenv("GLASSDOME_MODE", "unknown"),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "task_id"):
            log_entry["task_id"] = record.task_id
        if hasattr(record, "lab_id"):
            log_entry["lab_id"] = record.lab_id
        if hasattr(record, "vm_id"):
            log_entry["vm_id"] = record.vm_id
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        
        return json.dumps(log_entry)


class TaskLogger:
    """
    Context manager for task-level logging.
    
    Usage:
        with TaskLogger(task_id="abc123", lab_id="lab-xyz") as log:
            log.info("Starting task")
            # ... do work ...
            log.info("Task complete", duration_ms=1234)
    """
    
    def __init__(self, task_id: str = None, lab_id: str = None, **extra):
        self.task_id = task_id
        self.lab_id = lab_id
        self.extra = extra
        self.logger = logging.getLogger("glassdome.task")
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.error(f"Task failed: {exc_val}")
        return False
    
    def _log(self, level: int, message: str, **kwargs):
        extra = {
            "task_id": self.task_id,
            "lab_id": self.lab_id,
            **self.extra,
            **kwargs
        }
        
        # Calculate duration if we have a start time
        if self.start_time and "duration_ms" not in extra:
            extra["duration_ms"] = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        
        record = self.logger.makeRecord(
            self.logger.name,
            level,
            "(task)",
            0,
            message,
            (),
            None
        )
        for key, value in extra.items():
            setattr(record, key, value)
        
        self.logger.handle(record)
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)


def setup_worker_logging():
    """
    Configure logging for container workers.
    
    - JSON format for structured logging
    - stdout for Docker log collection
    - File rotation for persistent debugging
    """
    worker_id = os.getenv("WORKER_ID", "worker")
    worker_type = os.getenv("GLASSDOME_MODE", "unknown")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_dir = os.getenv("LOG_DIR", "/app/logs")
    
    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers = []
    
    # Console handler (stdout for Docker)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)
    
    # File handler (rotating, for debugging)
    log_file = os.path.join(log_dir, f"{worker_type}-{worker_id}.log")
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)
    
    # Log startup
    logging.info(f"Worker logging initialized", extra={
        "worker_id": worker_id,
        "worker_type": worker_type,
        "log_file": log_file
    })
    
    return root_logger

