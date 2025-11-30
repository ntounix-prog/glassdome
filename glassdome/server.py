"""
Server module

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

from glassdome.main import app
from glassdome.core.config import settings
from glassdome.core.security import ensure_security_context
from glassdome.core.logging import setup_logging_from_settings


def run(host: str = "0.0.0.0", port: int = None):
    """
    Run the Glassdome server
    
    Args:
        host: Host to bind to
        port: Port to bind to (defaults to settings.backend_port or 8010)
    """
    import uvicorn

    # Configure centralized logging
    setup_logging_from_settings()
    
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

