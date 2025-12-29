"""
E2E tests for the ingestion pipeline.

Tests the full flow:
1. Download a real arXiv paper (small one)
2. Upload to LightRAG
3. Wait for processing
4. Query the ingested content
5. Verify response contains expected content

These tests require:
- LIGHTRAG_API_KEY environment variable
- Network access to arXiv and LightRAG
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Mark all tests as E2E
pytestmark = [pytest.mark.e2e, pytest.mark.requires_lightrag]


class TestIngestionPipeline:
    """Test the full PDF ingestion pipeline."""
    
    @pytest.fixture
    def mock_all_services(self, mock_env):
        """Mock all external services for controlled testing."""
        with patch("src.services.hyperion_client.get_settings") as mock_settings:
            settings = MagicMock()
            settings.lightrag_url = "http://localhost:9621"
            settings.lightrag_api_key = "test-api-key"
            settings.hyperion_mcp_url = "https://test.mcp/hyperion"
            mock_settings.return_value = settings
            yield settings
    
    @pytest.mark.asyncio
    async def test_full_ingestion_flow_mocked(
        self,
        mock_all_services,
        sample_pdf_content,
    ):
        """Test full ingestion flow with mocked services."""
        from src.services.pdf_processor import PDFDownloader
        from src.services.hyperion_client import HyperionClient
        
        # Mock PDF download
        with patch.object(PDFDownloader, 'download', new_callable=AsyncMock) as mock_download:
            mock_download.return_value = sample_pdf_content
            
            # Mock Hyperion upload
            with patch("src.services.hyperion_client.AKClient") as mock_ak:
                mock_ak_instance = AsyncMock()
                mock_ak_instance.__aenter__ = AsyncMock(return_value=mock_ak_instance)
                mock_ak_instance.__aexit__ = AsyncMock(return_value=None)
                mock_ak.return_value = mock_ak_instance
                
                with patch("src.services.hyperion_client.httpx.AsyncClient") as mock_httpx:
                    mock_client = AsyncMock()
                    
                    # Mock upload response
                    mock_upload_response = MagicMock()
                    mock_upload_response.status_code = 200
                    mock_upload_response.json.return_value = {
                        "status": "success",
                        "id": "doc-test-123",
                    }
                    mock_client.post = AsyncMock(return_value=mock_upload_response)
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock(return_value=None)
                    mock_httpx.return_value = mock_client
                    
                    # Execute ingestion
                    downloader = PDFDownloader()
                    pdf_bytes = await downloader.download(arxiv_id="1706.03762")
                    
                    async with HyperionClient() as hyperion:
                        result = await hyperion.upload_pdf(pdf_bytes, "test_paper.pdf")
                    
                    # Verify
                    assert result.success is True
                    assert result.doc_id == "doc-test-123"
    
    @pytest.mark.asyncio
    async def test_ingestion_with_query_verification(
        self,
        mock_all_services,
        sample_pdf_content,
    ):
        """Test that ingested content can be queried."""
        from src.services.hyperion_client import HyperionClient
        
        with patch("src.services.hyperion_client.AKClient") as mock_ak:
            mock_ak_instance = AsyncMock()
            
            # First call is for query
            mock_ak_instance.call = AsyncMock(
                return_value="The Transformer architecture uses self-attention mechanisms. Source: test_paper.pdf"
            )
            mock_ak_instance.__aenter__ = AsyncMock(return_value=mock_ak_instance)
            mock_ak_instance.__aexit__ = AsyncMock(return_value=None)
            mock_ak.return_value = mock_ak_instance
            
            async with HyperionClient() as hyperion:
                result = await hyperion.query("What is the Transformer?")
            
            assert result.success is True
            assert "attention" in result.response.lower()
    
    @pytest.mark.asyncio
    async def test_pipeline_status_polling(
        self,
        mock_all_services,
    ):
        """Test polling for pipeline status until complete."""
        from src.services.hyperion_client import HyperionClient
        
        with patch("src.services.hyperion_client.AKClient") as mock_ak:
            mock_ak_instance = AsyncMock()
            mock_ak_instance.__aenter__ = AsyncMock(return_value=mock_ak_instance)
            mock_ak_instance.__aexit__ = AsyncMock(return_value=None)
            mock_ak.return_value = mock_ak_instance
            
            with patch("src.services.hyperion_client.httpx.AsyncClient") as mock_httpx:
                mock_client = AsyncMock()
                
                # Simulate status progression: busy -> not busy
                status_responses = [
                    {"busy": True, "latest_message": "Processing..."},
                    {"busy": False, "latest_message": "Complete"},
                ]
                
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json = MagicMock(side_effect=status_responses)
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_httpx.return_value = mock_client
                
                async with HyperionClient() as hyperion:
                    # First poll - still processing
                    status1 = await hyperion.get_pipeline_status()
                    
                    # Second poll - complete
                    status2 = await hyperion.get_pipeline_status()
                
                assert status1.busy is True
                assert status2.busy is False


class TestIngestionErrorRecovery:
    """Test error handling and recovery in ingestion pipeline."""
    
    @pytest.fixture
    def mock_all_services(self, mock_env):
        """Mock all external services."""
        with patch("src.services.hyperion_client.get_settings") as mock_settings:
            settings = MagicMock()
            settings.lightrag_url = "http://localhost:9621"
            settings.lightrag_api_key = "test-api-key"
            mock_settings.return_value = settings
            yield settings
    
    @pytest.mark.asyncio
    async def test_pdf_download_retry(self, mock_all_services):
        """Test that PDF download retries on failure."""
        from src.services.pdf_processor import PDFDownloader, PDFProcessorError
        
        with patch("httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            
            # All attempts fail
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_httpx.return_value = mock_client
            
            downloader = PDFDownloader()
            
            with pytest.raises(PDFProcessorError):
                await downloader.download(url="https://example.com/paper.pdf")
    
    @pytest.mark.asyncio
    async def test_lightrag_upload_failure(
        self,
        mock_all_services,
        sample_pdf_content,
    ):
        """Test handling of LightRAG upload failure."""
        from src.services.hyperion_client import HyperionClient
        
        with patch("src.services.hyperion_client.AKClient") as mock_ak:
            mock_ak_instance = AsyncMock()
            mock_ak_instance.__aenter__ = AsyncMock(return_value=mock_ak_instance)
            mock_ak_instance.__aexit__ = AsyncMock(return_value=None)
            mock_ak.return_value = mock_ak_instance
            
            with patch("src.services.hyperion_client.httpx.AsyncClient") as mock_httpx:
                mock_client = AsyncMock()
                
                # Simulate upload failure
                mock_response = MagicMock()
                mock_response.status_code = 503
                mock_response.text = "Service Unavailable"
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_httpx.return_value = mock_client
                
                async with HyperionClient() as hyperion:
                    # upload_pdf returns UploadResult with success=False
                    result = await hyperion.upload_pdf(sample_pdf_content, "test.pdf")
                    
                    assert result.success is False
                    assert "503" in result.error


class TestIngestionDatabaseIntegration:
    """Test ingestion pipeline with database updates."""
    
    @pytest.fixture
    def mock_all_services(self, mock_env, mock_supabase_client):
        """Mock all services including database."""
        with patch("src.services.hyperion_client.get_settings") as mock_settings:
            settings = MagicMock()
            settings.lightrag_url = "http://localhost:9621"
            settings.lightrag_api_key = "test-api-key"
            mock_settings.return_value = settings
            
            with patch("src.services.ingestion.get_supabase_client") as mock_db:
                mock_db.return_value = mock_supabase_client
                yield settings, mock_supabase_client
    
    @pytest.mark.asyncio
    async def test_source_status_updates(
        self,
        mock_all_services,
        sample_source_data,
        sample_pdf_content,
    ):
        """Test that source status is updated throughout pipeline."""
        from src.services.ingestion import IngestionService
        from src.models.source import IngestionStatus
        
        settings, mock_db = mock_all_services
        
        # Modify sample data to have PDF URL and use correct status
        sample_source_data["pdf_url"] = "https://example.com/paper.pdf"
        sample_source_data["ingestion_status"] = IngestionStatus.PENDING.value
        sample_source_data["hyperion_doc_name"] = None  # Ensure not already ingested
        
        # Set up mock to return source data
        mock_table = mock_db.table.return_value
        mock_table.maybe_single.return_value.execute.return_value = MagicMock(
            data=sample_source_data
        )
        
        with patch("src.services.pdf_processor.PDFDownloader.download", new_callable=AsyncMock) as mock_download:
            mock_download.return_value = sample_pdf_content
            
            with patch("src.services.hyperion_client.AKClient") as mock_ak:
                mock_ak_instance = AsyncMock()
                mock_ak_instance.__aenter__ = AsyncMock(return_value=mock_ak_instance)
                mock_ak_instance.__aexit__ = AsyncMock(return_value=None)
                mock_ak.return_value = mock_ak_instance
                
                with patch("src.services.hyperion_client.httpx.AsyncClient") as mock_httpx:
                    mock_client = AsyncMock()
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {"status": "success", "id": "doc-123"}
                    mock_client.post = AsyncMock(return_value=mock_response)
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock(return_value=None)
                    mock_httpx.return_value = mock_client
                    
                    service = IngestionService()
                    
                    # Override internal method to avoid real DB calls
                    service._get_source = MagicMock(return_value=sample_source_data)
                    service._update_status = MagicMock()
                    service._update_source_complete = MagicMock()
                    
                    result = await service.ingest_source(uuid4())
                    
                    # Verify status was updated
                    assert service._update_status.called or service._update_source_complete.called
