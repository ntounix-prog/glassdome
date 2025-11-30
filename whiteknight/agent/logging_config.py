"""
WhiteKnight Agent Logging Configuration

Mirrors the main Glassdome logging system for consistency.
Runs standalone in container without requiring full glassdome package.

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
import logging
import logging.handlers
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
import threading

# Thread-local storage for request context
_context = threading.local()


def set_log_context(**kwargs):
    """Set contextual data for log entries"""
    if not hasattr(_context, 'data'):
        _context.data = {}
    _context.data.update(kwargs)


def clear_log_context():
    """Clear the logging context"""
    _context.data = {}


def get_log_context() -> Dict[str, Any]:
    """Get current logging context"""
    return getattr(_context, 'data', {})


class JSONFormatter(logging.Formatter):
    """JSON formatter for SIEM-compatible log output."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "agent": "whiteknight"
        }
        
        context = get_log_context()
        if context:
            log_entry.update(context)
        
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, '')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        msg = f"{color}{timestamp} {record.levelname:<8}{self.RESET} [{record.name}] {record.getMessage()}"
        
        context = get_log_context()
        if context:
            context_str = ' '.join(f"{k}={v}" for k, v in context.items())
            msg += f" ({context_str})"
        
        if record.exc_info:
            msg += f"\n{self.formatException(record.exc_info)}"
        
        return msg


def setup_logging(
    level: str = None,
    log_dir: str = None,
    json_enabled: bool = True,
    console_enabled: bool = True,
) -> None:
    """
    Configure logging for WhiteKnight agent.
    
    Reads from environment variables for container configuration:
    - LOG_LEVEL: DEBUG, INFO, WARNING, ERROR (default: INFO)
    - LOG_DIR: Directory for log files (default: /var/log/whiteknight)
    - LOG_JSON_ENABLED: Enable JSON output (default: true)
    """
    # Get config from environment or arguments
    level = level or os.environ.get('LOG_LEVEL', 'INFO')
    log_dir = log_dir or os.environ.get('LOG_DIR', '/var/log/whiteknight')
    json_enabled = json_enabled if json_enabled is not None else os.environ.get('LOG_JSON_ENABLED', 'true').lower() == 'true'
    
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    
    # Console handler
    if console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(ColoredFormatter())
        root_logger.addHandler(console_handler)
    
    # Plain text file handler
    text_handler = logging.handlers.RotatingFileHandler(
        log_path / "whiteknight.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    text_handler.setLevel(log_level)
    text_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)-8s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    root_logger.addHandler(text_handler)
    
    # JSON file handler for SIEM
    if json_enabled:
        json_handler = logging.handlers.RotatingFileHandler(
            log_path / "whiteknight.json",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.INFO)
        json_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(json_handler)
    
    logger = logging.getLogger("whiteknight")
    logger.info(f"WhiteKnight logging initialized: level={level}, dir={log_dir}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
