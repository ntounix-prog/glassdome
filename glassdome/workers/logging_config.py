"""
Worker Logging Configuration

Provides logging setup for Celery workers and container-based services.
This module is called by the container entrypoint script.

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
import os
import logging


def setup_worker_logging():
    """
    Configure logging for workers running in containers.
    
    Reads LOG_LEVEL from environment and sets up logging
    before the worker starts.
    """
    # Import and use the centralized logging system
    from glassdome.core.logging import setup_logging
    
    # Get configuration from environment
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    log_dir = os.environ.get('LOG_DIR', '/app/logs')
    worker_id = os.environ.get('WORKER_ID', 'default')
    mode = os.environ.get('GLASSDOME_MODE', 'worker')
    
    # JSON enabled by default for container logs (easier to ship to ELK)
    json_enabled = os.environ.get('LOG_JSON_ENABLED', 'true').lower() == 'true'
    
    # Setup centralized logging
    setup_logging(
        level=log_level,
        log_dir=log_dir,
        json_enabled=json_enabled,
        console_enabled=True,
        file_enabled=True,
    )
    
    logger = logging.getLogger("glassdome.workers")
    logger.info(f"Worker logging initialized: mode={mode}, worker_id={worker_id}, level={log_level}")


if __name__ == "__main__":
    # Can be run directly to test
    setup_worker_logging()
    logger = logging.getLogger("glassdome.workers.test")
    logger.info("Test log message")
    logger.debug("Debug message (visible if LOG_LEVEL=DEBUG)")
    logger.warning("Warning message")
