"""
Unit tests for PDFDownloader.

Tests:
- arXiv URL pattern matching
- Filename generation
- Download logic (mocked)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestArxivUrlPattern:
    """Test arXiv URL pattern matching."""
    
    def test_arxiv_abs_url(self):
        """Test matching arXiv abstract URLs."""
        from src.services.pdf_processor import ARXIV_PDF_PATTERN
        
        url = "https://arxiv.org/abs/1706.03762"
        match = ARXIV_PDF_PATTERN.search(url)
        
        assert match is not None
        assert match.group(1) == "1706.03762"
    
    def test_arxiv_pdf_url(self):
        """Test matching arXiv PDF URLs."""
        from src.services.pdf_processor import ARXIV_PDF_PATTERN
        
        url = "https://arxiv.org/pdf/2301.00000"
        match = ARXIV_PDF_PATTERN.search(url)
        
        assert match is not None
        assert match.group(1) == "2301.00000"
    
    def test_arxiv_url_with_version(self):
        """Test arXiv URL with version number."""
        from src.services.pdf_processor import ARXIV_PDF_PATTERN
        
        # Pattern extracts base ID without version
        url = "https://arxiv.org/abs/1706.03762v1"
        match = ARXIV_PDF_PATTERN.search(url)
        
        # Should match the numeric part
        assert match is not None
    
    def test_non_arxiv_url(self):
        """Test non-arXiv URLs don't match."""
        from src.services.pdf_processor import ARXIV_PDF_PATTERN
        
        url = "https://example.com/paper.pdf"
        match = ARXIV_PDF_PATTERN.search(url)
        
        assert match is None


class TestFilenameGeneration:
    """Test PDF filename generation."""
    
    def test_filename_from_title(self):
        """Test generating filename from paper title."""
        from src.services.pdf_processor import PDFDownloader
        
        downloader = PDFDownloader()
        filename = downloader.generate_filename(
            title="Attention Is All You Need"
        )
        
        assert filename.endswith(".pdf")
        assert "Attention" in filename
        # No special characters
        assert "?" not in filename
        assert ":" not in filename
    
    def test_filename_from_arxiv_id(self):
        """Test generating filename from arXiv ID."""
        from src.services.pdf_processor import PDFDownloader
        
        downloader = PDFDownloader()
        filename = downloader.generate_filename(
            arxiv_id="1706.03762"
        )
        
        assert filename == "arxiv_1706.03762.pdf"
    
    def test_filename_from_doi(self):
        """Test generating filename from DOI."""
        from src.services.pdf_processor import PDFDownloader
        
        downloader = PDFDownloader()
        filename = downloader.generate_filename(
            doi="10.48550/arXiv.1706.03762"
        )
        
        assert filename.startswith("doi_")
        assert filename.endswith(".pdf")
        # Slashes replaced
        assert "/" not in filename
    
    def test_filename_fallback(self):
        """Test fallback filename when no identifiers provided."""
        from src.services.pdf_processor import PDFDownloader
        
        downloader = PDFDownloader()
        filename = downloader.generate_filename()
        
        assert filename == "document.pdf"
    
    def test_filename_title_truncation(self):
        """Test that long titles are truncated."""
        from src.services.pdf_processor import PDFDownloader
        
        downloader = PDFDownloader()
        long_title = "A" * 200  # Very long title
        filename = downloader.generate_filename(title=long_title)
        
        # Should be truncated to reasonable length
        assert len(filename) <= 110  # 100 chars + ".pdf"


class TestPDFDownload:
    """Test PDF download functionality (mocked)."""
    
    @pytest.mark.asyncio
    async def test_download_from_direct_url(self, mock_http_response, sample_pdf_content):
        """Test downloading from a direct PDF URL."""
        from src.services.pdf_processor import PDFDownloader
        
        mock_response = mock_http_response(
            status_code=200,
            content=sample_pdf_content,
            headers={"content-type": "application/pdf"},
        )
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client
            
            downloader = PDFDownloader()
            result = await downloader.download(url="https://example.com/paper.pdf")
            
            assert result == sample_pdf_content
            mock_client.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_download_from_arxiv(self, mock_http_response, sample_pdf_content):
        """Test downloading from arXiv using ID."""
        from src.services.pdf_processor import PDFDownloader
        
        mock_response = mock_http_response(
            status_code=200,
            content=sample_pdf_content,
            headers={"content-type": "application/pdf"},
        )
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client
            
            downloader = PDFDownloader()
            result = await downloader.download(arxiv_id="1706.03762")
            
            assert result == sample_pdf_content
            # Should have called with arXiv URL
            call_url = mock_client.get.call_args[0][0]
            assert "arxiv.org" in call_url
            assert "1706.03762" in call_url
    
    @pytest.mark.asyncio
    async def test_download_failure_raises_error(self, mock_http_response):
        """Test that failed downloads raise PDFProcessorError."""
        from src.services.pdf_processor import PDFDownloader, PDFProcessorError
        
        # All attempts fail
        mock_response = mock_http_response(status_code=404)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client
            
            downloader = PDFDownloader()
            
            with pytest.raises(PDFProcessorError) as exc_info:
                await downloader.download(url="https://example.com/missing.pdf")
            
            assert "Failed to download" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_download_fallback_order(self, mock_http_response, sample_pdf_content):
        """Test that download tries sources in order: URL, arXiv, Unpaywall."""
        from src.services.pdf_processor import PDFDownloader
        
        # First call (URL) fails, second (arXiv) succeeds
        mock_fail = mock_http_response(status_code=404)
        mock_success = mock_http_response(
            status_code=200,
            content=sample_pdf_content,
            headers={"content-type": "application/pdf"},
        )
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=[mock_fail, mock_success])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client
            
            downloader = PDFDownloader()
            result = await downloader.download(
                url="https://broken.com/paper.pdf",
                arxiv_id="1706.03762",
            )
            
            # Should succeed with arXiv fallback
            assert result == sample_pdf_content
            assert mock_client.get.call_count == 2

