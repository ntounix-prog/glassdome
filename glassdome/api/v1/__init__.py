"""
API v1 Router Aggregator

Aggregates all API routers under the /api/v1 prefix.
Provides backwards compatibility redirect from /api/* to /api/v1/*.

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from glassdome.core.config import settings

# Import all routers
from glassdome.api import auth
from glassdome.api import labs
from glassdome.api import ansible
from glassdome.api import chat
from glassdome.api import platforms
from glassdome.api import reaper
from glassdome.api import whiteknight
from glassdome.api import networks
from glassdome.api import whitepawn
from glassdome.api import canvas_deploy
from glassdome.api import container_dispatch
from glassdome.api import registry
from glassdome.api import secrets
from glassdome.api import network_probes
from glassdome.api import templates
from glassdome.api import agents_status
from glassdome.api import elements
from glassdome.api import ubuntu
from glassdome.api import reconciler
from glassdome.api import logs


# Create the main v1 router
# Note: Individual routers already have /api/* prefix
# We include them directly - they work at /api/*
# The v1 endpoint serves as a redirect layer

def get_all_routers():
    """Return all API routers to be included in the app."""
    return [
        auth.router,
        labs.router,
        ansible.router,
        chat.router,
        platforms.router,
        reaper.router,
        whiteknight.router,
        networks.router,
        whitepawn.router,
        canvas_deploy.router,
        container_dispatch.router,
        registry.router,
        secrets.router,
        network_probes.router,
        templates.router,
        agents_status.router,
        elements.router,
        ubuntu.router,
        reconciler.router,
        logs.router,
    ]


# V1 router for health and root endpoints
v1_router = APIRouter(prefix="/api/v1", tags=["v1"])


@v1_router.get("/health")
async def health_check_v1():
    """Health check endpoint (v1)."""
    return {
        "status": "healthy",
        "message": "Glassdome API v1 is running",
        "version": settings.app_version,
        "api_version": "v1"
    }


@v1_router.get("/")
async def root_v1():
    """Root API endpoint (v1)."""
    return {
        "message": "Glassdome - Agentic Cyber Range Deployment Framework",
        "version": settings.app_version,
        "api_version": "v1",
        "docs": "/docs"
    }


# Legacy redirect router - redirects /api/v1/* to /api/*
# This allows frontend to use /api/v1 while backend still uses /api
legacy_redirect_router = APIRouter()


@legacy_redirect_router.api_route(
    "/api/v1/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    include_in_schema=False
)
async def v1_to_legacy_redirect(path: str, request: Request):
    """
    Redirect /api/v1/* requests to /api/* endpoints.
    
    This provides backwards compatibility while transitioning to v1 API.
    Uses 307 to preserve HTTP method.
    """
    # Reconstruct the URL with /api/ prefix instead of /api/v1/
    new_url = f"/api/{path}"
    
    # Preserve query string
    if request.query_params:
        new_url += f"?{request.query_params}"
    
    return RedirectResponse(url=new_url, status_code=307)


def setup_v1_routes(app):
    """
    Set up v1 API routes on the FastAPI app.
    
    Call this from main.py to configure all routes.
    
    Args:
        app: FastAPI application instance
    """
    # Include the v1 router for /api/v1/health and /api/v1/
    app.include_router(v1_router)
    
    # Include the redirect router for /api/v1/* -> /api/*
    app.include_router(legacy_redirect_router)
    
    # Include all existing routers (at /api/*)
    for router in get_all_routers():
        app.include_router(router)
