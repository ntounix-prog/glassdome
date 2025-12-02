"""
Centralized Logging Configuration

Provides unified logging across all Glassdome modules with:
- Rotating file handlers (size-based)
- JSON output for SIEM integration (Filebeat/Logstash/ELK)
- Direct Logstash TCP shipping for real-time log aggregation
- Configurable log levels via environment
- Colored console output for development

Author: Brett Turner (ntounix)
Created: November 2025
Updated: December 2025 - Added Logstash TCP handler
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
import logging
import logging.handlers
import json
import sys
import socket
import os
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


class LogstashHandler(logging.Handler):
    """
    Handler for sending logs directly to Logstash via TCP.
    
    This provides real-time log shipping without requiring Filebeat,
    useful for containerized deployments.
    
    The handler:
    - Sends JSON-formatted logs over TCP
    - Automatically reconnects on connection failure
    - Buffers logs during connection issues
    - Adds metadata (hostname, application, etc.)
    """
    
    def __init__(
        self, 
        host: str = "192.168.3.26", 
        port: int = 5045,
        timeout: float = 5.0,
        max_buffer: int = 1000,
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.timeout = timeout
        self.max_buffer = max_buffer
        self.socket: Optional[socket.socket] = None
        self.buffer: list = []
        self._lock = threading.Lock()
        self._hostname = socket.gethostname()
        self._worker_id = os.getenv("WORKER_ID", "main")
        self._glassdome_mode = os.getenv("GLASSDOME_MODE", "backend")
    
    def _connect(self) -> bool:
        """Establish connection to Logstash."""
        try:
            if self.socket:
                try:
                    self.socket.close()
                except Exception:
                    pass
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            return True
        except Exception:
            self.socket = None
            return False
    
    def _send(self, message: str) -> bool:
        """Send a message to Logstash."""
        if not self.socket:
            if not self._connect():
                return False
        
        try:
            # Logstash expects newline-delimited JSON
            data = (message + "\n").encode('utf-8')
            self.socket.sendall(data)
            return True
        except Exception:
            self.socket = None
            return False
    
    def _flush_buffer(self):
        """Attempt to send buffered messages."""
        while self.buffer:
            message = self.buffer[0]
            if self._send(message):
                self.buffer.pop(0)
            else:
                break
    
    def emit(self, record: logging.LogRecord):
        """Emit a log record to Logstash."""
        try:
            # Build log entry
            log_entry = {
                "@timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "application": "glassdome",
                "host": self._hostname,
                "worker_id": self._worker_id,
                "glassdome_mode": self._glassdome_mode,
            }
            
            # Add context
            context = get_log_context()
            if context:
                log_entry.update(context)
            
            # Add exception info
            if record.exc_info:
                log_entry["exception"] = self.formatException(record.exc_info)
                log_entry["has_exception"] = True
            
            # Add extra fields
            for key, value in record.__dict__.items():
                if key not in ('name', 'msg', 'args', 'created', 'filename', 
                              'funcName', 'levelname', 'levelno', 'lineno',
                              'module', 'msecs', 'pathname', 'process',
                              'processName', 'relativeCreated', 'stack_info',
                              'exc_info', 'exc_text', 'thread', 'threadName',
                              'message', 'taskName'):
                    if not key.startswith('_'):
                        try:
                            # Ensure value is JSON serializable
                            json.dumps(value)
                            log_entry[key] = value
                        except (TypeError, ValueError):
                            log_entry[key] = str(value)
            
            message = json.dumps(log_entry)
            
            with self._lock:
                # Try to flush buffer first
                self._flush_buffer()
                
                # Send current message
                if not self._send(message):
                    # Buffer on failure (with limit)
                    if len(self.buffer) < self.max_buffer:
                        self.buffer.append(message)
        
        except Exception:
            # Don't let logging errors break the application
            self.handleError(record)
    
    def close(self):
        """Close the handler and socket."""
        with self._lock:
            if self.socket:
                try:
                    self.socket.close()
                except Exception:
                    pass
                self.socket = None
        super().close()


def setup_logging(
    level: str = "INFO",
    log_dir: str = "logs",
    max_size_mb: int = 10,
    backup_count: int = 5,
    json_enabled: bool = True,
    console_enabled: bool = True,
    file_enabled: bool = True,
    logstash_enabled: bool = None,
    logstash_host: str = None,
    logstash_port: int = None,
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
        logstash_enabled: Enable direct Logstash TCP output (default: from env)
        logstash_host: Logstash host (default: from env or 192.168.3.26)
        logstash_port: Logstash TCP port (default: from env or 5045)
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
    
    # Logstash TCP handler for real-time log shipping
    # Get settings from environment if not provided
    if logstash_enabled is None:
        logstash_enabled = os.getenv("LOGSTASH_ENABLED", "false").lower() in ("true", "1", "yes")
    if logstash_host is None:
        logstash_host = os.getenv("LOGSTASH_HOST", "192.168.3.26")
    if logstash_port is None:
        logstash_port = int(os.getenv("LOGSTASH_PORT", "5045"))
    
    if logstash_enabled:
        try:
            logstash_handler = LogstashHandler(
                host=logstash_host,
                port=logstash_port,
            )
            logstash_handler.setLevel(logging.INFO)  # Always INFO+ for Logstash
            root_logger.addHandler(logstash_handler)
        except Exception as e:
            # Don't fail startup if Logstash is unreachable
            print(f"Warning: Could not initialize Logstash handler: {e}", file=sys.stderr)
    
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
    if logstash_enabled:
        logger.info(f"Logstash TCP handler enabled: {logstash_host}:{logstash_port}")


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
        logstash_enabled=settings.logstash_enabled,
        logstash_host=settings.logstash_host,
        logstash_port=settings.logstash_port,
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
