"""
Pydantic models for Academic Research Tool.

This package contains all request/response models and database schemas.
"""

from src.models.common import (
    APIResponse,
    ErrorResponse,
    HealthResponse,
    PaginatedResponse,
    UserContext,
)
from src.models.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListItem,
    ProjectStatus,
)
from src.models.outline import (
    OutlineSectionCreate,
    OutlineSectionUpdate,
    OutlineSectionReorder,
    OutlineSectionResponse,
    OutlineSectionWithChildren,
    OutlineTree,
    SectionType,
)

__all__ = [
    # Common
    "APIResponse",
    "ErrorResponse", 
    "HealthResponse",
    "PaginatedResponse",
    "UserContext",
    # Project
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectListItem",
    "ProjectStatus",
    # Outline
    "OutlineSectionCreate",
    "OutlineSectionUpdate",
    "OutlineSectionReorder",
    "OutlineSectionResponse",
    "OutlineSectionWithChildren",
    "OutlineTree",
    "SectionType",
]

