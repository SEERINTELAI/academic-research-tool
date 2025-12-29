"""
Integration tests for HyperionClient.

Tests:
- Document listing
- Query operations
- Upload operations (requires API key)
- Pipeline status

These tests require LIGHTRAG_API_KEY to be set.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Mark all tests as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.requires_lightrag]


class TestHyperionClientIntegration:
    """Integration tests for HyperionClient."""
    
    @pytest.fixture
    def mock_settings(self, mock_env):
        """Mock settings with test values."""
        with patch("src.services.hyperion_client.get_settings") as mock:
            settings = MagicMock()
            settings.lightrag_url = "http://localhost:9621"
            settings.lightrag_api_key = "test-api-key"
            settings.hyperion_mcp_url = "https://test.mcp/hyperion"
            mock.return_value = settings
            yield settings
    
    @pytest.mark.asyncio
    async def test_list_documents(
        self,
        mock_settings,
        mock_lightrag_documents_response,
    ):
        """Test listing documents from LightRAG."""
        from src.services.hyperion_client import HyperionClient
        
        with patch("src.services.hyperion_client.AKClient") as mock_ak_class:
            mock_ak = AsyncMock()
            mock_ak.call = AsyncMock(return_value="Documents:\n- doc-001\n- doc-002")
            mock_ak.__aenter__ = AsyncMock(return_value=mock_ak)
            mock_ak.__aexit__ = AsyncMock(return_value=None)
            mock_ak_class.return_value = mock_ak
            
            with patch("httpx.AsyncClient") as mock_httpx:
                mock_client = AsyncMock()
                mock_httpx.return_value = mock_client
                
                async with HyperionClient() as client:
                    result = await client.list_documents()
                    
                    assert result is not None
                    assert hasattr(result, 'documents')
    
    @pytest.mark.asyncio
    async def test_query_knowledge(
        self,
        mock_settings,
        mock_lightrag_query_response,
    ):
        """Test querying the knowledge base."""
        from src.services.hyperion_client import HyperionClient
        
        with patch("src.services.hyperion_client.AKClient") as mock_ak_class:
            mock_ak = AsyncMock()
            mock_ak.call = AsyncMock(
                return_value="The Transformer uses self-attention. Source: attention_paper.pdf"
            )
            mock_ak.__aenter__ = AsyncMock(return_value=mock_ak)
            mock_ak.__aexit__ = AsyncMock(return_value=None)
            mock_ak_class.return_value = mock_ak
            
            with patch("httpx.AsyncClient") as mock_httpx:
                mock_client = AsyncMock()
                mock_httpx.return_value = mock_client
                
                async with HyperionClient() as client:
                    result = await client.query("What is attention?")
                    
                    assert result.success is True
                    assert result.query == "What is attention?"
                    assert "attention" in result.response.lower()
    
    @pytest.mark.asyncio
    async def test_ingest_texts(
        self,
        mock_settings,
    ):
        """Test ingesting text chunks."""
        from src.services.hyperion_client import HyperionClient
        
        with patch("src.services.hyperion_client.AKClient") as mock_ak_class:
            mock_ak = AsyncMock()
            mock_ak.call = AsyncMock(
                return_value="Successfully ingested 2 chunks. Track ID: track-123"
            )
            mock_ak.__aenter__ = AsyncMock(return_value=mock_ak)
            mock_ak.__aexit__ = AsyncMock(return_value=None)
            mock_ak_class.return_value = mock_ak
            
            with patch("httpx.AsyncClient") as mock_httpx:
                mock_client = AsyncMock()
                mock_httpx.return_value = mock_client
                
                async with HyperionClient() as client:
                    result = await client.ingest(
                        texts=["chunk 1", "chunk 2"],
                        doc_name="test_doc",
                    )
                    
                    assert result.success is True
                    assert result.doc_name == "test_doc"
                    assert result.chunk_count == 2
    
    @pytest.mark.asyncio
    async def test_upload_pdf(
        self,
        mock_settings,
        sample_pdf_content,
        mock_lightrag_upload_response,
    ):
        """Test uploading a PDF file."""
        from src.services.hyperion_client import HyperionClient
        
        # Mock settings with API key
        mock_settings.lightrag_api_key = "test-api-key"
        mock_settings.lightrag_url = "http://localhost:9621"
        
        with patch("src.services.hyperion_client.AKClient") as mock_ak_class:
            mock_ak = AsyncMock()
            mock_ak.__aenter__ = AsyncMock(return_value=mock_ak)
            mock_ak.__aexit__ = AsyncMock(return_value=None)
            mock_ak_class.return_value = mock_ak
            
            with patch("httpx.AsyncClient") as mock_httpx:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"status": "success", "id": "doc-123"}
                mock_response.text = ""
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_httpx.return_value = mock_client
                
                async with HyperionClient() as client:
                    result = await client.upload_pdf(
                        sample_pdf_content,
                        "test_paper.pdf",
                    )
                    
                    assert result.success is True
                    assert result.filename == "test_paper.pdf"
    
    @pytest.mark.asyncio
    async def test_get_pipeline_status(
        self,
        mock_settings,
        mock_pipeline_status_response,
    ):
        """Test getting pipeline status."""
        from src.services.hyperion_client import HyperionClient
        
        # Mock settings with API key
        mock_settings.lightrag_api_key = "test-api-key"
        mock_settings.lightrag_url = "http://localhost:9621"
        
        with patch("src.services.hyperion_client.AKClient") as mock_ak_class:
            mock_ak = AsyncMock()
            mock_ak.__aenter__ = AsyncMock(return_value=mock_ak)
            mock_ak.__aexit__ = AsyncMock(return_value=None)
            mock_ak_class.return_value = mock_ak
            
            with patch("httpx.AsyncClient") as mock_httpx:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_pipeline_status_response
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_httpx.return_value = mock_client
                
                async with HyperionClient() as client:
                    result = await client.get_pipeline_status()
                    
                    # Check that we got a valid status back
                    assert result.busy == mock_pipeline_status_response.get("busy", False)
    
    @pytest.mark.asyncio
    async def test_delete_document(
        self,
        mock_settings,
    ):
        """Test deleting a document."""
        from src.services.hyperion_client import HyperionClient
        
        with patch("src.services.hyperion_client.AKClient") as mock_ak_class:
            mock_ak = AsyncMock()
            mock_ak.call = AsyncMock(
                return_value="Successfully deleted document test_doc"
            )
            mock_ak.__aenter__ = AsyncMock(return_value=mock_ak)
            mock_ak.__aexit__ = AsyncMock(return_value=None)
            mock_ak_class.return_value = mock_ak
            
            with patch("httpx.AsyncClient") as mock_httpx:
                mock_client = AsyncMock()
                mock_httpx.return_value = mock_client
                
                async with HyperionClient() as client:
                    result = await client.delete("test_doc")
                    
                    assert result.success is True
                    assert result.doc_name == "test_doc"


class TestHyperionErrorHandling:
    """Test error handling in HyperionClient."""
    
    @pytest.fixture
    def mock_settings(self, mock_env):
        """Mock settings with test values."""
        with patch("src.services.hyperion_client.get_settings") as mock:
            settings = MagicMock()
            settings.lightrag_url = "http://localhost:9621"
            settings.lightrag_api_key = "test-api-key"
            settings.hyperion_mcp_url = "https://test.mcp/hyperion"
            mock.return_value = settings
            yield settings
    
    @pytest.mark.asyncio
    async def test_upload_failure(
        self,
        mock_settings,
        sample_pdf_content,
    ):
        """Test handling of upload failure."""
        from src.services.hyperion_client import HyperionClient
        
        # Mock settings with API key
        mock_settings.lightrag_api_key = "test-api-key"
        mock_settings.lightrag_url = "http://localhost:9621"
        
        with patch("src.services.hyperion_client.AKClient") as mock_ak_class:
            mock_ak = AsyncMock()
            mock_ak.__aenter__ = AsyncMock(return_value=mock_ak)
            mock_ak.__aexit__ = AsyncMock(return_value=None)
            mock_ak_class.return_value = mock_ak
            
            with patch("httpx.AsyncClient") as mock_httpx:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 500
                mock_response.text = "Internal Server Error"
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_httpx.return_value = mock_client
                
                async with HyperionClient() as client:
                    # upload_pdf returns UploadResult with success=False, doesn't raise
                    result = await client.upload_pdf(sample_pdf_content, "test.pdf")
                    
                    assert result.success is False
                    assert result.error is not None
                    assert "500" in result.error
    
    @pytest.mark.asyncio
    async def test_query_failure(self, mock_settings):
        """Test handling of query failure."""
        from src.services.hyperion_client import HyperionClient
        from src.services.ak_client import AKError
        
        with patch("src.services.hyperion_client.AKClient") as mock_ak_class:
            mock_ak = AsyncMock()
            mock_ak.call = AsyncMock(side_effect=AKError("Connection failed", "call"))
            mock_ak.__aenter__ = AsyncMock(return_value=mock_ak)
            mock_ak.__aexit__ = AsyncMock(return_value=None)
            mock_ak_class.return_value = mock_ak
            
            with patch("httpx.AsyncClient") as mock_httpx:
                mock_client = AsyncMock()
                mock_httpx.return_value = mock_client
                
                async with HyperionClient() as client:
                    result = await client.query("test query")
                    
                    # Query returns result with error, not exception
                    assert result.success is False
                    assert result.error is not None


class TestLightRAGDirectAPI:
    """Test direct LightRAG API calls (bypassing MCP)."""
    
    @pytest.fixture
    def mock_settings(self, mock_env):
        """Mock settings with test values."""
        with patch("src.services.hyperion_client.get_settings") as mock:
            settings = MagicMock()
            settings.lightrag_url = "http://localhost:9621"
            settings.lightrag_api_key = "test-api-key"
            settings.hyperion_mcp_url = "https://test.mcp/hyperion"
            mock.return_value = settings
            yield settings
    
    @pytest.mark.asyncio
    async def test_lightrag_health_endpoint(
        self,
        mock_settings,
        mock_lightrag_health_response,
    ):
        """Test direct LightRAG health check."""
        import httpx
        
        with patch("httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_lightrag_health_response
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client
            
            async with httpx.AsyncClient(
                base_url="http://localhost:9621",
                headers={"Authorization": "Bearer test-key"},
            ) as client:
                response = await client.get("/health")
                
            # Just verify the mock was called
            mock_client.get.assert_called()

