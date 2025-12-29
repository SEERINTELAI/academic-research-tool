"""
Academic Research Tool - FastAPI Application

Main entry point for the API server.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.api import api_router
from src.config import get_settings
from src.models.common import ErrorResponse
from src.api.routes.health import log_request, log_error

# Configure structured JSON logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

# Add filter to inject request_id into all log records
class RequestIdFilter(logging.Filter):
    """Filter that adds request_id to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, 'request_id'):
            record.request_id = '-'
        return True

# Apply filter to root logger
for handler in logging.root.handlers:
    handler.addFilter(RequestIdFilter())

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    Handles startup and shutdown events.
    """
    # Startup
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds request ID and logs all requests.
    
    Features:
    - Generates unique request ID for each request
    - Logs request start/end with timing
    - Records requests to diagnostics buffer
    - Adds X-Request-ID header to responses
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]
        
        # Store in request state for access in handlers
        request.state.request_id = request_id
        
        # Get request info
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        
        # Start timing
        start_time = time.time()
        
        # Log request start
        logger.info(
            f"➡️  {method} {path} from {client_ip}",
            extra={"request_id": request_id}
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log request completion
            status_emoji = "✅" if response.status_code < 400 else "❌"
            logger.info(
                f"{status_emoji} {method} {path} -> {response.status_code} ({duration_ms:.1f}ms)",
                extra={"request_id": request_id}
            )
            
            # Record to diagnostics buffer
            log_request({
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "client_ip": client_ip,
            })
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Log error
            duration_ms = (time.time() - start_time) * 1000
            logger.exception(
                f"💥 {method} {path} FAILED ({duration_ms:.1f}ms): {e}",
                extra={"request_id": request_id}
            )
            
            # Record error to diagnostics buffer
            log_error({
                "request_id": request_id,
                "method": method,
                "path": path,
                "error": str(e),
                "error_type": type(e).__name__,
            })
            
            raise


def create_app() -> FastAPI:
    """
    Application factory.
    
    Creates and configures the FastAPI application.
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-powered academic research assistant for paper writing",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )
    
    # Add request logging middleware (must be added before CORS)
    app.add_middleware(RequestLoggingMiddleware)
    
    # Add CORS middleware
    # In development, allow all origins (including Cursor browser's vscode-webview origin)
    if settings.is_development:
        # Use allow_origin_regex to match any origin in dev mode
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r".*",  # Match any origin
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Include API routes
    app.include_router(api_router, prefix="/api")
    
    # Root endpoint
    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs" if settings.is_development else None,
            "health": "/api/health",
        }
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle uncaught exceptions."""
        request_id = getattr(request.state, 'request_id', 'unknown')
        logger.exception(
            f"Unhandled exception: {exc}",
            extra={"request_id": request_id}
        )
        
        # Record to error buffer
        log_error({
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "error": str(exc),
            "error_type": type(exc).__name__,
        })
        
        # Don't expose internal errors in production
        if settings.is_production:
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error="Internal server error",
                    code="internal_error",
                ).model_dump(mode="json"),
                headers={"X-Request-ID": request_id},
            )
        else:
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error="Internal server error",
                    detail=str(exc),
                    code="internal_error",
                ).model_dump(mode="json"),
                headers={"X-Request-ID": request_id},
            )
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
    )

