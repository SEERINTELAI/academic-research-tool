"""
Project Pydantic models.

Models for research project CRUD operations.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    """Project status enumeration."""
    
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectCreate(BaseModel):
    """Request model for creating a project."""
    
    title: str = Field(..., min_length=1, max_length=500, description="Project title")
    description: Optional[str] = Field(None, max_length=5000, description="Project description")


class ProjectUpdate(BaseModel):
    """Request model for updating a project."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[ProjectStatus] = None


class ProjectResponse(BaseModel):
    """Response model for a single project."""
    
    id: UUID
    title: str
    description: Optional[str] = None
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ProjectListItem(BaseModel):
    """Response model for project list items."""
    
    id: UUID
    title: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    
    # Computed fields (populated by query)
    source_count: int = 0
    outline_section_count: int = 0
    
    model_config = {"from_attributes": True}


class ProjectWithOutline(ProjectResponse):
    """Project response with outline sections included."""
    
    outline_sections: list["OutlineSectionResponse"] = []


# Forward reference for OutlineSectionResponse
from src.models.outline import OutlineSectionResponse  # noqa: E402

ProjectWithOutline.model_rebuild()

