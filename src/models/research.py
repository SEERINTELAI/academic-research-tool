"""
Research Query Pydantic models.

Models for RAG queries against ingested academic papers.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class QueryMode(str, Enum):
    """Query mode for RAG retrieval."""
    
    SIMPLE = "simple"  # Direct query
    HYBRID = "hybrid"  # Combined keyword + semantic
    MULTI_HOP = "multi_hop"  # Follow references


class CitationStyle(str, Enum):
    """Citation formatting style."""
    
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    IEEE = "ieee"
    INLINE = "inline"  # Just (Author, Year)


class SourceReference(BaseModel):
    """Reference to a source used in synthesis."""
    
    source_id: UUID
    chunk_id: Optional[UUID] = None
    
    # Citation info
    title: str
    authors: list[str] = []
    publication_year: Optional[int] = None
    doi: Optional[str] = None
    
    # Location in source
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    
    # Retrieved text
    retrieved_text: str = ""
    relevance_score: Optional[float] = None
    
    # Formatted citation
    in_text_citation: Optional[str] = None  # e.g., "(Smith, 2023)"
    full_citation: Optional[str] = None  # Full reference entry


class QueryRequest(BaseModel):
    """Request for RAG query."""
    
    query: str = Field(..., min_length=1, max_length=2000)
    
    # Query options
    mode: QueryMode = QueryMode.SIMPLE
    max_sources: int = Field(default=5, ge=1, le=20)
    citation_style: CitationStyle = CitationStyle.APA
    
    # Filtering
    source_ids: Optional[list[UUID]] = None  # Limit to specific sources
    section_types: Optional[list[str]] = None  # e.g., ["methods", "results"]
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    
    # Response options
    include_quotes: bool = True
    include_context: bool = True
    max_response_tokens: int = Field(default=1000, ge=100, le=4000)


class QueryResponse(BaseModel):
    """Response from RAG query."""
    
    query: str
    answer: str = Field(..., description="Synthesized answer with inline citations")
    
    # Sources used
    sources: list[SourceReference] = Field(default_factory=list)
    
    # Metadata
    total_chunks_searched: int = 0
    processing_time_ms: int = 0
    
    # For display
    formatted_references: Optional[str] = None  # Full reference list


class SynthesisCreate(BaseModel):
    """Request to save a synthesis."""
    
    project_id: UUID
    query: str
    answer: str
    sources: list[SourceReference] = []
    
    # Optional linking
    outline_section_id: Optional[UUID] = None
    
    # User edits
    user_notes: Optional[str] = None
    is_pinned: bool = False


class SynthesisResponse(BaseModel):
    """Response model for a saved synthesis."""
    
    id: UUID
    project_id: UUID
    query: str
    answer: str
    sources: list[SourceReference]
    
    # Linking
    outline_section_id: Optional[UUID] = None
    
    # User edits
    user_notes: Optional[str] = None
    is_pinned: bool
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class SynthesisListItem(BaseModel):
    """Lightweight synthesis for list views."""
    
    id: UUID
    query: str
    answer_preview: str = Field(..., max_length=200)
    source_count: int = 0
    is_pinned: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}


class CompareRequest(BaseModel):
    """Request to compare findings across sources."""
    
    topic: str = Field(..., min_length=1, max_length=500)
    source_ids: list[UUID] = Field(..., min_items=2, max_items=10)
    aspects: Optional[list[str]] = None  # Specific aspects to compare


class CompareResponse(BaseModel):
    """Response from source comparison."""
    
    topic: str
    comparison_table: list[dict] = []  # Structured comparison data
    narrative: str = ""  # Written comparison
    sources: list[SourceReference] = []

