"""
Centralized Logging Configuration

Provides unified logging across all Glassdome modules with:
- Rotating file handlers (size-based)
- JSON output for SIEM integration (Filebeat/Logstash/ELK)
- Configurable log levels via environment
- Colored console output for development

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
import logging
import logging.handlers
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
import threading

# Thread-local storage for request context
_context = threading.local()


def set_log_context(**kwargs):
    """Set contextual data for log entries (request_id, user, etc.)"""
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
    """
    JSON formatter for SIEM-compatible log output.
    
    Produces logs like:
    {
        "timestamp": "2025-11-30T15:30:45.123Z",
        "level": "INFO",
        "logger": "glassdome.api.labs",
        "message": "Lab deployed successfully",
        "request_id": "req-xyz789",
        "user": "admin"
    }
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add context (request_id, user, etc.)
        context = get_log_context()
        if context:
            log_entry.update(context)
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add any extra fields from the record
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'created', 'filename', 
                          'funcName', 'levelname', 'levelno', 'lineno',
                          'module', 'msecs', 'pathname', 'process',
                          'processName', 'relativeCreated', 'stack_info',
                          'exc_info', 'exc_text', 'thread', 'threadName',
                          'message', 'taskName'):
                if not key.startswith('_'):
                    log_entry[key] = value
        
        return json.dumps(log_entry)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for development."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        # Add color based on level
        color = self.COLORS.get(record.levelname, '')
        
        # Format timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Build message
        msg = f"{color}{timestamp} {record.levelname:<8}{self.RESET} [{record.name}] {record.getMessage()}"
        
        # Add context if present
        context = get_log_context()
        if context:
            context_str = ' '.join(f"{k}={v}" for k, v in context.items())
            msg += f" ({context_str})"
        
        # Add exception if present
        if record.exc_info:
            msg += f"\n{self.formatException(record.exc_info)}"
        
        return msg


class PlainFormatter(logging.Formatter):
    """Plain text formatter for file logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        msg = f"{timestamp} {record.levelname:<8} [{record.name}] {record.getMessage()}"
        
        context = get_log_context()
        if context:
            context_str = ' '.join(f"{k}={v}" for k, v in context.items())
            msg += f" ({context_str})"
        
        if record.exc_info:
            msg += f"\n{self.formatException(record.exc_info)}"
        
        return msg


def setup_logging(
    level: str = "INFO",
    log_dir: str = "logs",
    max_size_mb: int = 10,
    backup_count: int = 5,
    json_enabled: bool = True,
    console_enabled: bool = True,
    file_enabled: bool = True,
) -> None:
    """
    Configure centralized logging for Glassdome.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files
        max_size_mb: Max file size before rotation (MB)
        backup_count: Number of backup files to keep
        json_enabled: Enable JSON output file for SIEM
        console_enabled: Enable console output
        file_enabled: Enable text file output
    """
    # Convert level string to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Calculate max bytes
    max_bytes = max_size_mb * 1024 * 1024
    
    # Console handler
    if console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(ColoredFormatter())
        root_logger.addHandler(console_handler)
    
    # Plain text file handler
    if file_enabled:
        text_handler = logging.handlers.RotatingFileHandler(
            log_path / "glassdome.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        text_handler.setLevel(log_level)
        text_handler.setFormatter(PlainFormatter())
        root_logger.addHandler(text_handler)
        
        # Debug file (only when DEBUG level)
        if log_level == logging.DEBUG:
            debug_handler = logging.handlers.RotatingFileHandler(
                log_path / "glassdome-debug.log",
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(PlainFormatter())
            root_logger.addHandler(debug_handler)
    
    # JSON file handler for SIEM
    if json_enabled:
        json_handler = logging.handlers.RotatingFileHandler(
            log_path / "glassdome.json",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.INFO)  # Always INFO+ for JSON (not DEBUG noise)
        json_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(json_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger("glassdome.core.logging")
    logger.info(f"Logging initialized: level={level}, dir={log_dir}")
    if json_enabled:
        logger.info(f"JSON logs enabled at {log_path / 'glassdome.json'} (SIEM-ready)")


def setup_logging_from_settings() -> None:
    """
    Configure logging from application settings.
    
    This is the primary entry point - call this once at application startup.
    """
    # Import here to avoid circular imports
    from glassdome.core.config import settings
    
    setup_logging(
        level=settings.log_level,
        log_dir=settings.log_dir,
        max_size_mb=settings.log_max_size_mb,
        backup_count=settings.log_backup_count,
        json_enabled=settings.log_json_enabled,
        console_enabled=settings.log_console_enabled,
        file_enabled=settings.log_file_enabled,
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    This is a convenience wrapper around logging.getLogger().
    Usage: logger = get_logger(__name__)
    """
    return logging.getLogger(name)


# Module-level convenience functions
def debug(msg: str, **kwargs):
    """Log debug message with optional context."""
    set_log_context(**kwargs)
    logging.getLogger("glassdome").debug(msg)


def info(msg: str, **kwargs):
    """Log info message with optional context."""
    set_log_context(**kwargs)
    logging.getLogger("glassdome").info(msg)


def warning(msg: str, **kwargs):
    """Log warning message with optional context."""
    set_log_context(**kwargs)
    logging.getLogger("glassdome").warning(msg)


def error(msg: str, **kwargs):
    """Log error message with optional context."""
    set_log_context(**kwargs)
    logging.getLogger("glassdome").error(msg)
