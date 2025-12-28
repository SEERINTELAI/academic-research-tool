"""
API package for Academic Research Tool.

This package contains all API routes and dependencies.
"""

from fastapi import APIRouter

from src.api.routes import health, projects, outline

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"],
)

api_router.include_router(
    projects.router,
    prefix="/projects",
    tags=["projects"],
)

# Outline routes are nested under projects
api_router.include_router(
    outline.router,
    prefix="/projects/{project_id}/outline",
    tags=["outline"],
)

# Future routes will be added here:
# api_router.include_router(sources.router, prefix="/projects/{project_id}/sources", tags=["sources"])
# api_router.include_router(research.router, prefix="/projects/{project_id}/research", tags=["research"])
# api_router.include_router(reports.router, prefix="/projects/{project_id}/reports", tags=["reports"])

__all__ = ["api_router"]

