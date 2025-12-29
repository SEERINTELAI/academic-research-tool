"""
Pytest configuration and shared fixtures.

Provides:
- Async test support
- Environment mocking
- Database fixtures
- API client fixtures
- Sample data fixtures
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import httpx

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: fast isolated tests (no external dependencies)")
    config.addinivalue_line("markers", "integration: tests with external services")
    config.addinivalue_line("markers", "e2e: full end-to-end pipeline tests")
    config.addinivalue_line("markers", "requires_lightrag: needs LIGHTRAG_API_KEY")
    config.addinivalue_line("markers", "requires_supabase: needs Supabase connection")
    config.addinivalue_line("markers", "requires_semantic_scholar: needs Semantic Scholar API")


# =============================================================================
# Environment Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def test_env() -> dict[str, str]:
    """Load test environment variables."""
    # Try .env.test first, fall back to .env
    from dotenv import load_dotenv
    
    test_env_path = Path(__file__).parent.parent / ".env.test"
    if test_env_path.exists():
        load_dotenv(test_env_path)
    else:
        load_dotenv(Path(__file__).parent.parent / ".env")
    
    return {
        "SUPABASE_URL": os.getenv("SUPABASE_URL", ""),
        "SUPABASE_ANON_KEY": os.getenv("SUPABASE_ANON_KEY", ""),
        "LIGHTRAG_URL": os.getenv("LIGHTRAG_URL", "http://5.78.148.113:9621"),
        "LIGHTRAG_API_KEY": os.getenv("LIGHTRAG_API_KEY", ""),
        "SEMANTIC_SCHOLAR_API_KEY": os.getenv("SEMANTIC_SCHOLAR_API_KEY", ""),
    }


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables for testing."""
    env_vars = {
        "SUPABASE_URL": "https://test-project.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "LIGHTRAG_URL": "http://localhost:9621",
        "LIGHTRAG_API_KEY": "test-lightrag-key",
        "ENVIRONMENT": "development",
        "DEBUG": "true",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


# =============================================================================
# Skip Conditions
# =============================================================================

@pytest.fixture(scope="session")
def has_lightrag_key(test_env) -> bool:
    """Check if LightRAG API key is available."""
    return bool(test_env.get("LIGHTRAG_API_KEY"))


@pytest.fixture(scope="session")
def has_supabase(test_env) -> bool:
    """Check if Supabase is configured."""
    return bool(test_env.get("SUPABASE_URL") and test_env.get("SUPABASE_ANON_KEY"))


def skip_without_lightrag(has_lightrag_key):
    """Skip test if LightRAG API key is not available."""
    if not has_lightrag_key:
        pytest.skip("LIGHTRAG_API_KEY not configured")


def skip_without_supabase(has_supabase):
    """Skip test if Supabase is not configured."""
    if not has_supabase:
        pytest.skip("Supabase not configured")


# =============================================================================
# HTTP Mocking Fixtures
# =============================================================================

@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx AsyncClient."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


@pytest.fixture
def mock_http_response():
    """Factory for creating mock HTTP responses."""
    def _create_response(
        status_code: int = 200,
        json_data: dict = None,
        content: bytes = None,
        headers: dict = None,
    ):
        response = MagicMock(spec=httpx.Response)
        response.status_code = status_code
        response.headers = headers or {"content-type": "application/json"}
        if json_data is not None:
            response.json.return_value = json_data
        if content is not None:
            response.content = content
        response.text = str(json_data) if json_data else ""
        return response
    return _create_response


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_paper_data() -> dict:
    """Sample paper data from Semantic Scholar."""
    return {
        "paperId": "abc123",
        "title": "Attention Is All You Need",
        "abstract": "We propose a new simple network architecture, the Transformer...",
        "year": 2017,
        "venue": "NeurIPS",
        "authors": [
            {"authorId": "1", "name": "Ashish Vaswani"},
            {"authorId": "2", "name": "Noam Shazeer"},
        ],
        "externalIds": {
            "DOI": "10.48550/arXiv.1706.03762",
            "ArXiv": "1706.03762",
        },
        "isOpenAccess": True,
        "openAccessPdf": {
            "url": "https://arxiv.org/pdf/1706.03762.pdf",
        },
        "citationCount": 50000,
        "fieldsOfStudy": ["Computer Science"],
    }


@pytest.fixture
def sample_search_response(sample_paper_data) -> dict:
    """Sample Semantic Scholar search response."""
    return {
        "total": 1,
        "offset": 0,
        "next": None,
        "data": [sample_paper_data],
    }


@pytest.fixture
def sample_project_data() -> dict:
    """Sample project data."""
    return {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "title": "Test Research Project",
        "description": "A test project for unit testing",
        "status": "active",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_source_data(sample_project_data) -> dict:
    """Sample source data."""
    return {
        "id": str(uuid4()),
        "project_id": sample_project_data["id"],
        "title": "Attention Is All You Need",
        "doi": "10.48550/arXiv.1706.03762",
        "arxiv_id": "1706.03762",
        "authors": [
            {"name": "Ashish Vaswani"},
            {"name": "Noam Shazeer"},
        ],
        "abstract": "We propose a new simple network architecture...",
        "publication_year": 2017,
        "journal": "NeurIPS",
        "pdf_url": "https://arxiv.org/pdf/1706.03762.pdf",
        "ingestion_status": "pending",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Sample PDF content (minimal valid PDF)."""
    # Minimal valid PDF structure
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
196
%%EOF"""


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    mock_client = MagicMock()
    
    # Mock table operations
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.range.return_value = mock_table
    mock_table.single.return_value = mock_table
    mock_table.maybe_single.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[])
    
    mock_client.table.return_value = mock_table
    return mock_client


# =============================================================================
# LightRAG Fixtures
# =============================================================================

@pytest.fixture
def mock_lightrag_health_response() -> dict:
    """Mock LightRAG health response."""
    return {
        "status": "healthy",
        "webui_available": True,
        "working_directory": "/app/data/rag_storage",
        "configuration": {
            "llm_model": "gpt-4o",
            "embedding_model": "text-embedding-3-large",
        },
        "auth_mode": "disabled",
        "pipeline_busy": False,
        "core_version": "v1.4.9.10",
    }


@pytest.fixture
def mock_lightrag_upload_response() -> dict:
    """Mock LightRAG document upload response."""
    return {
        "status": "success",
        "id": "doc-abc123",
        "message": "Document uploaded successfully",
    }


@pytest.fixture
def mock_lightrag_query_response() -> dict:
    """Mock LightRAG query response."""
    return {
        "response": "The Transformer architecture uses self-attention mechanisms...",
        "references": [
            {
                "reference_id": "ref-001",
                "file_path": "attention_paper.pdf",
                "content": ["Self-attention allows the model to attend to all positions..."],
            }
        ],
    }


@pytest.fixture
def mock_lightrag_documents_response() -> dict:
    """Mock LightRAG documents list response."""
    return {
        "statuses": {
            "PROCESSED": ["doc-001", "doc-002"],
            "PENDING": [],
            "PROCESSING": [],
            "FAILED": [],
        }
    }


@pytest.fixture
def mock_pipeline_status_response() -> dict:
    """Mock LightRAG pipeline status response."""
    return {
        "autoscanned": True,
        "busy": False,
        "job_name": None,
        "docs": 5,
        "batchs": 1,
        "cur_batch": 1,
        "latest_message": "Idle",
    }


# =============================================================================
# Cleanup Fixtures
# =============================================================================

@pytest.fixture
def cleanup_test_projects(has_supabase, test_env):
    """
    Fixture to track and cleanup test projects after tests.
    
    Usage:
        def test_something(cleanup_test_projects):
            project_id = create_project(...)
            cleanup_test_projects.append(project_id)
    """
    project_ids = []
    yield project_ids
    
    if has_supabase and project_ids:
        # Cleanup would happen here with real DB
        pass

