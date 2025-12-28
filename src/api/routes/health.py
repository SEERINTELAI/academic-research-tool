"""
Health check endpoints.

Provides system health and readiness checks.
"""

import logging
from datetime import datetime

from fastapi import APIRouter

from src.config import get_settings
from src.models.common import HealthResponse
from src.services.database import check_database_connection

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=HealthResponse,
    summary="Health check",
    description="Check if the API is healthy and return service status.",
)
async def health_check() -> HealthResponse:
    """
    Check API health status.
    
    Returns basic health information including version and environment.
    Also checks database connectivity.
    """
    settings = get_settings()
    
    # Check database
    db_healthy = await check_database_connection()
    db_status = "healthy" if db_healthy else "unhealthy"
    
    # TODO: Add Hyperion health check when client is implemented
    hyperion_status = "not_checked"
    
    # Overall status
    overall_status = "healthy" if db_healthy else "degraded"
    
    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.utcnow(),
        database=db_status,
        hyperion=hyperion_status,
    )


@router.get(
    "/ready",
    summary="Readiness check",
    description="Check if the API is ready to accept traffic.",
)
async def readiness_check() -> dict:
    """
    Check if the API is ready to accept traffic.
    
    This is a lightweight check for load balancers and orchestrators.
    """
    return {"ready": True}


@router.get(
    "/live",
    summary="Liveness check",
    description="Check if the API process is alive.",
)
async def liveness_check() -> dict:
    """
    Check if the API process is alive.
    
    This is the most basic check - if this fails, restart the container.
    """
    return {"alive": True}

