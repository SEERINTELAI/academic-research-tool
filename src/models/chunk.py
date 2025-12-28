"""
Chunk Pydantic models.

Models for academic paper chunks used in RAG.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChunkType(str, Enum):
    """Type of chunk content."""
    
    TITLE = "title"
    ABSTRACT = "abstract"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    REFERENCE = "reference"
    FIGURE_CAPTION = "figure_caption"
    TABLE_CAPTION = "table_caption"


class ChunkMetadata(BaseModel):
    """Metadata attached to each chunk for provenance."""
    
    # Source identification
    source_id: UUID
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    
    # Document location
    section_type: Optional[str] = None  # From GROBID section classification
    section_title: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    
    # Content info
    chunk_index: int = 0  # Position in document
    total_chunks: int = 0
    
    # Citation info (for generating in-text citations)
    authors: list[str] = []
    publication_year: Optional[int] = None
    title: Optional[str] = None


class ChunkCreate(BaseModel):
    """Request to create a chunk."""
    
    source_id: UUID
    chunk_type: ChunkType
    content: str = Field(..., min_length=1)
    
    # Metadata
    section_type: Optional[str] = None
    section_title: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    chunk_index: int = 0
    total_chunks: int = 0
    
    # Embedding info (populated after ingestion)
    embedding_id: Optional[str] = None  # ID in vector store


class ChunkResponse(BaseModel):
    """Response model for a chunk."""
    
    id: UUID
    source_id: UUID
    chunk_type: ChunkType
    content: str
    
    # Metadata
    section_type: Optional[str] = None
    section_title: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    chunk_index: int
    total_chunks: int
    
    # Ingestion
    hyperion_id: Optional[str] = None
    token_count: int = 0
    
    # Timestamps
    created_at: datetime
    
    model_config = {"from_attributes": True}


class ChunkWithContext(ChunkResponse):
    """Chunk with surrounding context for display."""
    
    # Source info for citation
    source_title: Optional[str] = None
    source_authors: list[str] = []
    source_year: Optional[int] = None
    source_doi: Optional[str] = None
    
    # Navigation
    prev_chunk_id: Optional[UUID] = None
    next_chunk_id: Optional[UUID] = None


class ChunkForIngestion(BaseModel):
    """Chunk formatted for Hyperion ingestion."""
    
    id: UUID
    text: str  # Content with embedded metadata
    doc_name: str  # For Hyperion document name
    
    # Raw content (without metadata prefix)
    raw_content: str
    
    # Metadata for later retrieval
    metadata: ChunkMetadata


class ChunkerConfig(BaseModel):
    """Configuration for the chunking strategy."""
    
    # Size limits
    max_chunk_tokens: int = Field(default=512, ge=100, le=2000)
    min_chunk_tokens: int = Field(default=50, ge=10, le=200)
    
    # Overlap
    overlap_tokens: int = Field(default=50, ge=0, le=200)
    
    # Section handling
    split_on_sections: bool = True
    preserve_paragraphs: bool = True
    
    # Metadata embedding
    embed_metadata_in_text: bool = True
    metadata_template: str = "[Source: {title} | Section: {section} | Page: {page}]\n\n"

