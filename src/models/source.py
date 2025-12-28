"""
Source (Academic Paper) Pydantic models.

Models for paper search, metadata, and ingestion tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class IngestionStatus(str, Enum):
    """Paper ingestion pipeline status."""
    
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PARSING = "parsing"
    CHUNKING = "chunking"
    INGESTING = "ingesting"
    READY = "ready"
    FAILED = "failed"


class Author(BaseModel):
    """Academic paper author."""
    
    name: str
    author_id: Optional[str] = None  # Semantic Scholar author ID
    affiliation: Optional[str] = None
    orcid: Optional[str] = None


class PaperSearchResult(BaseModel):
    """Search result from academic API (Semantic Scholar, etc.)."""
    
    # Identifiers
    paper_id: str = Field(..., description="External API paper ID")
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    
    # Metadata
    title: str
    authors: list[Author] = []
    abstract: Optional[str] = None
    publication_year: Optional[int] = None
    venue: Optional[str] = None  # Journal/conference name
    
    # Availability
    is_open_access: bool = False
    pdf_url: Optional[str] = None
    
    # Metrics
    citation_count: Optional[int] = None
    reference_count: Optional[int] = None
    
    # Source API
    source_api: str = "semantic_scholar"


class PaperSearchRequest(BaseModel):
    """Request to search for papers."""
    
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=20, ge=1, le=100)
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    open_access_only: bool = False
    fields_of_study: list[str] = []


class PaperSearchResponse(BaseModel):
    """Response from paper search."""
    
    query: str
    total_results: int
    results: list[PaperSearchResult]
    next_offset: Optional[int] = None  # For pagination


class SourceCreate(BaseModel):
    """Request to add a paper to a project."""
    
    # From search result
    paper_id: str
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    title: str
    authors: list[Author] = []
    abstract: Optional[str] = None
    publication_year: Optional[int] = None
    venue: Optional[str] = None
    pdf_url: Optional[str] = None
    
    # Additional metadata
    keywords: list[str] = []
    notes: Optional[str] = None


class SourceResponse(BaseModel):
    """Response model for a source in the database."""
    
    id: UUID
    project_id: UUID
    
    # Identifiers
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    
    # Metadata
    title: str
    authors: list[Author] = []
    abstract: Optional[str] = None
    publication_year: Optional[int] = None
    journal: Optional[str] = None
    
    # URLs
    pdf_url: Optional[str] = None
    
    # Ingestion
    ingestion_status: IngestionStatus
    hyperion_doc_name: Optional[str] = None
    chunk_count: int = 0
    error_message: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class SourceListItem(BaseModel):
    """Lightweight source for list views."""
    
    id: UUID
    title: str
    authors: list[Author] = []
    publication_year: Optional[int] = None
    ingestion_status: IngestionStatus
    chunk_count: int = 0
    created_at: datetime
    
    model_config = {"from_attributes": True}


class SourceIngestRequest(BaseModel):
    """Request to ingest a source into Hyperion."""
    
    source_id: UUID
    force_reprocess: bool = False  # Re-ingest even if already processed

