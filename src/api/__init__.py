"""
API package for Academic Research Tool.

This package contains all API routes and dependencies.
"""

from fastapi import APIRouter

from src.api.routes import health, projects, outline, sources, research, discovery, logs, research_agent, chat

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

# Sources routes for paper management
api_router.include_router(
    sources.router,
    prefix="/projects/{project_id}/sources",
    tags=["sources"],
)

# Research routes for RAG queries
api_router.include_router(
    research.router,
    prefix="/projects/{project_id}/research",
    tags=["research"],
)

# Discovery routes for knowledge tree / citation graph
api_router.include_router(
    discovery.router,
    prefix="/projects/{project_id}/sources",
    tags=["discovery"],
)

# AI Research Agent routes (legacy)
api_router.include_router(
    research_agent.router,
    prefix="/projects/{project_id}/agent",
    tags=["research-agent"],
)

# Chat-driven research UI routes
api_router.include_router(
    chat.router,
    prefix="/projects/{project_id}/research-ui",
    tags=["research-ui"],
)

# Frontend logging endpoint (no auth required)
api_router.include_router(
    logs.router,
    tags=["logs"],
)

# Future routes will be added here:
# api_router.include_router(reports.router, prefix="/projects/{project_id}/reports", tags=["reports"])

__all__ = ["api_router"]

