"""
Server module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""

import logging
import sys

from glassdome.main import app
from glassdome.core.config import settings
from glassdome.core.security import ensure_security_context


def configure_logging():
    """Configure logging for the application"""
    # Root logger configuration
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout
    )
    
    # Enable DEBUG for chat and LLM modules for troubleshooting
    logging.getLogger("glassdome.chat").setLevel(logging.DEBUG)
    logging.getLogger("glassdome.api.chat").setLevel(logging.DEBUG)
    
    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)
    logging.getLogger("anthropic").setLevel(logging.INFO)


def run(host: str = "0.0.0.0", port: int = None):
    """
    Run the Glassdome server
    
    Args:
        host: Host to bind to
        port: Port to bind to (defaults to settings.backend_port or 8010)
    """
    import uvicorn

    # Configure logging first
    configure_logging()
    
    # Ensure this process has a valid security context (no prompts here).
    # If the session hasn't been initialized on this host/user, this will
    # raise with guidance to run ./glassdome_start or login via API.
    ensure_security_context()
    
    port = port or getattr(settings, "backend_port", 8010)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    run()

