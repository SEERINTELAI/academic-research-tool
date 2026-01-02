"""
Service layer for Academic Research Tool.

Contains business logic and external service integrations.
"""

from src.services.database import get_supabase_client, SupabaseClient
from src.services.auth import (
    verify_token,
    get_current_user,
    AuthError,
)
from src.services.ak_client import (
    AKClient,
    AKError,
    call_ak,
)
from src.services.hyperion_client import (
    HyperionClient,
    HyperionError,
    hyperion_list_documents,
    hyperion_query,
    hyperion_ingest,
    hyperion_delete,
    hyperion_upload_pdf,
    hyperion_pipeline_status,
)
from src.services.semantic_scholar import (
    SemanticScholarClient,
    SemanticScholarError,
    search_papers,
)
from src.services.openalex import (
    OpenAlexClient,
    OpenAlexError,
)
from src.services.arxiv import (
    ArxivClient,
    ArxivError,
    search_arxiv,
)
from src.services.pubmed import (
    PubMedClient,
    PubMedError,
    search_pubmed,
)
from src.services.crossref import (
    CrossRefClient,
    CrossRefError,
    search_crossref,
)
from src.services.core import (
    CoreClient,
    CoreError,
    search_core,
)
from src.services.multi_source_search import (
    MultiSourceSearchService,
    MultiSourceSearchResult,
    SearchSource,
    search_all_sources,
)
from src.services.pdf_processor import (
    PDFDownloader,
    PDFProcessorError,
    download_pdf,
)
from src.services.ingestion import (
    IngestionService,
    IngestionError,
    ingest_source,
    get_pipeline_status,
)
from src.services.query_service import (
    QueryService,
    QueryError,
    query_project,
)
from src.services.discovery import (
    DiscoveryService,
    RelationType,
    discover_references,
    discover_citations,
    explore_knowledge_tree,
)

__all__ = [
    # Database
    "get_supabase_client",
    "SupabaseClient",
    # Auth
    "verify_token",
    "get_current_user",
    "AuthError",
    # AK
    "AKClient",
    "AKError",
    "call_ak",
    # Hyperion
    "HyperionClient",
    "HyperionError",
    "hyperion_list_documents",
    "hyperion_query",
    "hyperion_ingest",
    "hyperion_delete",
    "hyperion_upload_pdf",
    "hyperion_pipeline_status",
    # Semantic Scholar
    "SemanticScholarClient",
    "SemanticScholarError",
    "search_papers",
    # OpenAlex
    "OpenAlexClient",
    "OpenAlexError",
    # arXiv
    "ArxivClient",
    "ArxivError",
    "search_arxiv",
    # PubMed
    "PubMedClient",
    "PubMedError",
    "search_pubmed",
    # CrossRef
    "CrossRefClient",
    "CrossRefError",
    "search_crossref",
    # CORE
    "CoreClient",
    "CoreError",
    "search_core",
    # Multi-Source Search
    "MultiSourceSearchService",
    "MultiSourceSearchResult",
    "SearchSource",
    "search_all_sources",
    # PDF Downloader
    "PDFDownloader",
    "PDFProcessorError",
    "download_pdf",
    # Ingestion
    "IngestionService",
    "IngestionError",
    "ingest_source",
    "get_pipeline_status",
    # Query
    "QueryService",
    "QueryError",
    "query_project",
    # Discovery
    "DiscoveryService",
    "RelationType",
    "discover_references",
    "discover_citations",
    "explore_knowledge_tree",
]
