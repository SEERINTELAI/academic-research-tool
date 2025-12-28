"""
API package for Academic Research Tool.

This package contains all API routes and dependencies.
"""

from fastapi import APIRouter

from src.api.routes import health

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"],
)

# Future routes will be added here:
# api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
# api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
# api_router.include_router(research.router, prefix="/research", tags=["research"])
# api_router.include_router(reports.router, prefix="/reports", tags=["reports"])

__all__ = ["api_router"]

