"""
Health check endpoints.

Provides system health and readiness checks.
"""

import logging
from collections import deque
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.config import get_settings
from src.models.common import HealthResponse
from src.services.database import check_database_connection, get_supabase_client

logger = logging.getLogger(__name__)

# In-memory buffers for diagnostics
_recent_errors: deque = deque(maxlen=100)
_recent_requests: deque = deque(maxlen=100)


def log_error(error: dict) -> None:
    """Add an error to the recent errors buffer."""
    error["timestamp"] = datetime.utcnow().isoformat()
    _recent_errors.append(error)


def log_request(request: dict) -> None:
    """Add a request to the recent requests buffer."""
    request["timestamp"] = datetime.utcnow().isoformat()
    _recent_requests.append(request)

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


# =============================================================================
# Diagnostics Endpoint
# =============================================================================

class ServiceStatus(BaseModel):
    """Status of an external service."""
    name: str
    status: str  # healthy, unhealthy, degraded, unknown
    latency_ms: Optional[float] = None
    message: Optional[str] = None


class DiagnosticsResponse(BaseModel):
    """Comprehensive diagnostics response."""
    timestamp: datetime
    status: str
    version: str
    environment: str
    
    # Service health
    services: list[ServiceStatus]
    
    # Debugging info
    recent_errors: list[dict] = Field(default_factory=list)
    request_logs: list[dict] = Field(default_factory=list)
    
    # Metrics
    active_connections: int = 0
    projects_count: int = 0
    
    # Configuration (non-sensitive)
    config: dict = Field(default_factory=dict)


@router.get(
    "/diagnostics",
    response_model=DiagnosticsResponse,
    summary="System diagnostics",
    description="Get comprehensive system diagnostics for debugging.",
)
async def get_diagnostics() -> DiagnosticsResponse:
    """
    Get detailed system diagnostics.
    
    Returns:
    - Health status of all services (DB, LightRAG, external APIs)
    - Recent errors (last 100)
    - Recent request logs (last 100)
    - Active connection counts
    - Environment info
    """
    settings = get_settings()
    services = []
    
    # Check database
    db_start = datetime.utcnow()
    try:
        db_healthy = await check_database_connection()
        db_latency = (datetime.utcnow() - db_start).total_seconds() * 1000
        services.append(ServiceStatus(
            name="database",
            status="healthy" if db_healthy else "unhealthy",
            latency_ms=db_latency,
        ))
    except Exception as e:
        services.append(ServiceStatus(
            name="database",
            status="unhealthy",
            message=str(e),
        ))
    
    # Check LightRAG
    rag_start = datetime.utcnow()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.lightrag_url}/health")
            rag_latency = (datetime.utcnow() - rag_start).total_seconds() * 1000
            services.append(ServiceStatus(
                name="lightrag",
                status="healthy" if response.status_code == 200 else "degraded",
                latency_ms=rag_latency,
            ))
    except Exception as e:
        services.append(ServiceStatus(
            name="lightrag",
            status="unhealthy",
            message=str(e)[:100],
        ))
    
    # Check Semantic Scholar (simple connectivity)
    ss_start = datetime.utcnow()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1")
            ss_latency = (datetime.utcnow() - ss_start).total_seconds() * 1000
            services.append(ServiceStatus(
                name="semantic_scholar",
                status="healthy" if response.status_code == 200 else "degraded",
                latency_ms=ss_latency,
            ))
    except Exception as e:
        services.append(ServiceStatus(
            name="semantic_scholar",
            status="unknown",
            message=str(e)[:100],
        ))
    
    # Get project count
    projects_count = 0
    try:
        db = get_supabase_client()
        result = db.table("project").select("id", count="exact").execute()
        projects_count = result.count or 0
    except Exception:
        pass
    
    # Overall status
    unhealthy_count = sum(1 for s in services if s.status == "unhealthy")
    if unhealthy_count == 0:
        overall_status = "healthy"
    elif unhealthy_count < len(services):
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    return DiagnosticsResponse(
        timestamp=datetime.utcnow(),
        status=overall_status,
        version=settings.app_version,
        environment=settings.environment,
        services=services,
        recent_errors=list(_recent_errors),
        request_logs=list(_recent_requests)[-50:],  # Last 50 requests
        active_connections=0,  # TODO: Track active connections
        projects_count=projects_count,
        config={
            "host": settings.host,
            "port": settings.port,
            "debug": settings.debug,
            "cors_origins": settings.cors_origins,
            "lightrag_url": settings.lightrag_url,
            "hyperion_mcp_url": settings.hyperion_mcp_url,
        },
    )

