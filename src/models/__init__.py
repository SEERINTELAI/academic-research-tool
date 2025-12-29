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
from src.models.hyperion import (
    HyperionDocument,
    HyperionDocumentList,
    DocumentStatus,
    IngestRequest,
    IngestResult,
    QueryRequest,
    QueryResult,
    ChunkReference,
    DeleteResult,
    UploadResult,
    PipelineStatus,
)
from src.models.source import (
    Author,
    IngestionStatus,
    PaperSearchRequest,
    PaperSearchResult,
    PaperSearchResponse,
    SourceCreate,
    SourceResponse,
    SourceListItem,
    SourceIngestRequest,
)
from src.models.research import (
    QueryMode,
    CitationStyle,
    SourceReference,
    QueryRequest as ResearchQueryRequest,
    QueryResponse as ResearchQueryResponse,
    SynthesisCreate,
    SynthesisResponse,
    SynthesisListItem,
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
    # Hyperion
    "HyperionDocument",
    "HyperionDocumentList",
    "DocumentStatus",
    "IngestRequest",
    "IngestResult",
    "QueryRequest",
    "QueryResult",
    "ChunkReference",
    "DeleteResult",
    "UploadResult",
    "PipelineStatus",
    # Source
    "Author",
    "IngestionStatus",
    "PaperSearchRequest",
    "PaperSearchResult",
    "PaperSearchResponse",
    "SourceCreate",
    "SourceResponse",
    "SourceListItem",
    "SourceIngestRequest",
    # Research
    "QueryMode",
    "CitationStyle",
    "SourceReference",
    "ResearchQueryRequest",
    "ResearchQueryResponse",
    "SynthesisCreate",
    "SynthesisResponse",
    "SynthesisListItem",
]
