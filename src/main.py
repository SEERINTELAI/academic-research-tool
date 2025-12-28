"""
Academic Research Tool - FastAPI Application

Main entry point for the API server.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api import api_router
from src.config import get_settings
from src.models.common import ErrorResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
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
    
    # Add CORS middleware
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
        logger.exception(f"Unhandled exception: {exc}")
        
        # Don't expose internal errors in production
        if settings.is_production:
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error="Internal server error",
                    code="internal_error",
                ).model_dump(mode="json"),
            )
        else:
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error="Internal server error",
                    detail=str(exc),
                    code="internal_error",
                ).model_dump(mode="json"),
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

