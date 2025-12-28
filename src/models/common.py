"""
Common Pydantic models used across the application.
"""

from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Error response model."""
    
    success: bool = False
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = "healthy"
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Service status
    database: str = "unknown"
    hyperion: str = "unknown"


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    
    success: bool = True
    data: list[T]
    total: int
    page: int
    page_size: int
    has_more: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


class UserContext(BaseModel):
    """User context extracted from JWT token."""
    
    user_id: str
    email: Optional[str] = None
    role: str = "authenticated"
    
    # Token metadata
    token_exp: Optional[datetime] = None
    token_iat: Optional[datetime] = None

