"""
Glassdome Server - FastAPI Application Entry Point
Separated from main.py to allow package imports
"""
from glassdome.main import app
from glassdome.core.config import settings


def run(host: str = "0.0.0.0", port: int = None):
    """
    Run the Glassdome server
    
    Args:
        host: Host to bind to
        port: Port to bind to (defaults to settings.backend_port or 8001)
    """
    import uvicorn
    
    port = port or getattr(settings, 'backend_port', 8001)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    run()

