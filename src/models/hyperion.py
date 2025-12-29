"""
Hyperion RAG Pydantic models.

Models for Hyperion/LightRAG operations via AK MCP.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    """Document processing status in Hyperion."""
    
    PROCESSED = "processed"
    FAILED = "failed"
    PROCESSING = "processing"


class HyperionDocument(BaseModel):
    """A document stored in Hyperion/LightRAG."""
    
    name: str = Field(..., description="Document name/identifier")
    status: DocumentStatus = DocumentStatus.PROCESSED
    chunk_count: Optional[int] = None


class HyperionDocumentList(BaseModel):
    """Response from listing documents."""
    
    documents: list[HyperionDocument] = []
    total_count: int = 0
    failed_count: int = 0


class IngestRequest(BaseModel):
    """Request to ingest text chunks into Hyperion."""
    
    texts: list[str] = Field(..., min_length=1, description="Text chunks to ingest")
    doc_name: str = Field(..., description="Document name for all chunks")
    
    @property
    def doc_names(self) -> list[str]:
        """Generate doc_name array matching texts length."""
        return [self.doc_name] * len(self.texts)


class IngestResult(BaseModel):
    """Result of ingestion operation."""
    
    success: bool
    doc_name: str
    chunk_count: int
    track_id: Optional[str] = None
    error: Optional[str] = None


class QueryRequest(BaseModel):
    """Request to query Hyperion knowledge base."""
    
    query: str = Field(..., min_length=1, description="Natural language query")
    format: Optional[str] = Field(None, description="Optional format specification")


class ChunkReference(BaseModel):
    """Reference to a retrieved chunk."""
    
    doc_name: str
    text_preview: Optional[str] = None
    relevance_score: Optional[float] = None


class QueryResult(BaseModel):
    """Result of a RAG query."""
    
    success: bool
    query: str
    response: str
    sources: list[ChunkReference] = []
    error: Optional[str] = None


class DeleteResult(BaseModel):
    """Result of delete operation."""
    
    success: bool
    doc_name: str
    deleted_count: int = 0
    error: Optional[str] = None


class UploadResult(BaseModel):
    """Result of PDF upload operation."""
    
    success: bool
    filename: str
    doc_id: Optional[str] = None
    track_id: Optional[str] = None
    status: str = "pending"  # pending, processing, completed, failed
    error: Optional[str] = None


class PipelineStatus(BaseModel):
    """Status of the LightRAG processing pipeline."""
    
    busy: bool = False
    job_name: Optional[str] = None
    job_start: Optional[str] = None
    docs_count: int = 0
    batches: int = 0
    current_batch: int = 0
    latest_message: Optional[str] = None
    autoscanned: bool = False
    request_pending: bool = False

