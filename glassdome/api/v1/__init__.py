"""
API v1 Router Aggregator

All API routes are mounted under /api/v1/ prefix.

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
from fastapi import APIRouter

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
from glassdome.api import overseer


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
        overseer.router,
    ]


# V1 router for health and root endpoints
v1_router = APIRouter(tags=["v1"])


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


def setup_v1_routes(app):
    """
    Set up v1 API routes on the FastAPI app.
    
    All routes are mounted at /api/v1/*
    
    Args:
        app: FastAPI application instance
    """
    # Include the v1 health/root router at /api/v1
    app.include_router(v1_router, prefix="/api/v1")
    
    # Include all routers at /api/v1 (they have their own sub-prefixes like /reaper, /labs)
    for router in get_all_routers():
        app.include_router(router, prefix="/api/v1")
