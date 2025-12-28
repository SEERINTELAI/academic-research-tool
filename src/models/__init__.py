"""
Pydantic models for Academic Research Tool.

This package contains all request/response models and database schemas.
"""

from src.models.common import (
    APIResponse,
    ErrorResponse,
    HealthResponse,
    PaginatedResponse,
)

__all__ = [
    "APIResponse",
    "ErrorResponse", 
    "HealthResponse",
    "PaginatedResponse",
]

