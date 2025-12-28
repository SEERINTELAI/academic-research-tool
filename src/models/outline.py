"""
Outline Section Pydantic models.

Models for hierarchical research outline management.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SectionType(str, Enum):
    """Academic paper section types."""
    
    INTRODUCTION = "introduction"
    LITERATURE_REVIEW = "literature_review"
    METHODS = "methods"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    ABSTRACT = "abstract"
    CUSTOM = "custom"


class OutlineSectionCreate(BaseModel):
    """Request model for creating an outline section."""
    
    title: str = Field(..., min_length=1, max_length=500)
    section_type: SectionType = SectionType.CUSTOM
    parent_id: Optional[UUID] = Field(None, description="Parent section ID for nesting")
    questions: list[str] = Field(default_factory=list, description="Research questions for this section")
    notes: Optional[str] = Field(None, max_length=10000)
    order_index: Optional[int] = Field(None, description="Position within parent")


class OutlineSectionUpdate(BaseModel):
    """Request model for updating an outline section."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    section_type: Optional[SectionType] = None
    parent_id: Optional[UUID] = None
    questions: Optional[list[str]] = None
    notes: Optional[str] = Field(None, max_length=10000)
    order_index: Optional[int] = None


class OutlineSectionReorder(BaseModel):
    """Request model for reordering outline sections."""
    
    section_id: UUID
    new_parent_id: Optional[UUID] = None
    new_order_index: int


class OutlineSectionResponse(BaseModel):
    """Response model for a single outline section."""
    
    id: UUID
    project_id: UUID
    parent_id: Optional[UUID] = None
    title: str
    section_type: SectionType
    questions: list[str] = []
    notes: Optional[str] = None
    order_index: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class OutlineSectionWithChildren(OutlineSectionResponse):
    """Outline section with nested children."""
    
    children: list["OutlineSectionWithChildren"] = []


# Rebuild for self-reference
OutlineSectionWithChildren.model_rebuild()


class OutlineTree(BaseModel):
    """Complete outline tree for a project."""
    
    project_id: UUID
    sections: list[OutlineSectionWithChildren] = []
    total_count: int = 0

