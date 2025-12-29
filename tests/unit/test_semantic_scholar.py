"""
Unit tests for SemanticScholarClient.

Tests:
- Search query formatting
- Result parsing
- Rate limit handling
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestQueryFormatting:
    """Test search query parameter formatting."""
    
    @pytest.mark.asyncio
    async def test_basic_search_params(self, mock_http_response, sample_search_response):
        """Test basic search query parameters."""
        from src.services.semantic_scholar import SemanticScholarClient
        
        mock_response = mock_http_response(
            status_code=200,
            json_data=sample_search_response,
        )
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            client = SemanticScholarClient()
            client._client = mock_client
            
            await client.search("machine learning", limit=10)
            
            # Verify call was made with correct params
            call_args = mock_client.get.call_args
            params = call_args.kwargs.get("params", call_args[1].get("params", {}))
            
            assert params["query"] == "machine learning"
            assert params["limit"] == 10
            assert "fields" in params
    
    @pytest.mark.asyncio
    async def test_year_filter_range(self, mock_http_response, sample_search_response):
        """Test year range filter."""
        from src.services.semantic_scholar import SemanticScholarClient
        
        mock_response = mock_http_response(
            status_code=200,
            json_data=sample_search_response,
        )
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            client = SemanticScholarClient()
            client._client = mock_client
            
            await client.search("transformers", year_from=2020, year_to=2023)
            
            call_args = mock_client.get.call_args
            params = call_args.kwargs.get("params", call_args[1].get("params", {}))
            
            assert params["year"] == "2020-2023"
    
    @pytest.mark.asyncio
    async def test_year_filter_from_only(self, mock_http_response, sample_search_response):
        """Test year filter with only from year."""
        from src.services.semantic_scholar import SemanticScholarClient
        
        mock_response = mock_http_response(
            status_code=200,
            json_data=sample_search_response,
        )
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            client = SemanticScholarClient()
            client._client = mock_client
            
            await client.search("transformers", year_from=2020)
            
            call_args = mock_client.get.call_args
            params = call_args.kwargs.get("params", call_args[1].get("params", {}))
            
            assert params["year"] == "2020-"
    
    @pytest.mark.asyncio
    async def test_fields_of_study_filter(self, mock_http_response, sample_search_response):
        """Test fields of study filter."""
        from src.services.semantic_scholar import SemanticScholarClient
        
        mock_response = mock_http_response(
            status_code=200,
            json_data=sample_search_response,
        )
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            client = SemanticScholarClient()
            client._client = mock_client
            
            await client.search("AI", fields_of_study=["Computer Science", "Mathematics"])
            
            call_args = mock_client.get.call_args
            params = call_args.kwargs.get("params", call_args[1].get("params", {}))
            
            assert params["fieldsOfStudy"] == "Computer Science,Mathematics"
    
    @pytest.mark.asyncio
    async def test_limit_capped_at_100(self, mock_http_response, sample_search_response):
        """Test that limit is capped at 100."""
        from src.services.semantic_scholar import SemanticScholarClient
        
        mock_response = mock_http_response(
            status_code=200,
            json_data=sample_search_response,
        )
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            client = SemanticScholarClient()
            client._client = mock_client
            
            await client.search("AI", limit=500)  # Request more than allowed
            
            call_args = mock_client.get.call_args
            params = call_args.kwargs.get("params", call_args[1].get("params", {}))
            
            assert params["limit"] == 100  # Should be capped


class TestResultParsing:
    """Test parsing of API responses."""
    
    def test_parse_paper_full_data(self, sample_paper_data):
        """Test parsing a paper with all fields."""
        from src.services.semantic_scholar import SemanticScholarClient
        
        client = SemanticScholarClient()
        result = client._parse_paper(sample_paper_data)
        
        assert result.paper_id == "abc123"
        assert result.title == "Attention Is All You Need"
        assert result.abstract == "We propose a new simple network architecture, the Transformer..."
        assert result.publication_year == 2017
        assert result.venue == "NeurIPS"
        assert len(result.authors) == 2
        assert result.authors[0].name == "Ashish Vaswani"
        assert result.doi == "10.48550/arXiv.1706.03762"
        assert result.arxiv_id == "1706.03762"
        assert result.is_open_access is True
        assert result.pdf_url == "https://arxiv.org/pdf/1706.03762.pdf"
    
    def test_parse_paper_missing_optional_fields(self):
        """Test parsing a paper with missing optional fields."""
        from src.services.semantic_scholar import SemanticScholarClient
        
        minimal_data = {
            "paperId": "xyz789",
            "title": "Minimal Paper",
            "authors": [],
        }
        
        client = SemanticScholarClient()
        result = client._parse_paper(minimal_data)
        
        assert result.paper_id == "xyz789"
        assert result.title == "Minimal Paper"
        assert result.abstract is None
        assert result.doi is None
        assert result.arxiv_id is None
        assert result.pdf_url is None
        assert len(result.authors) == 0
    
    def test_parse_paper_null_external_ids(self):
        """Test parsing when externalIds is null."""
        from src.services.semantic_scholar import SemanticScholarClient
        
        data = {
            "paperId": "test123",
            "title": "Test Paper",
            "externalIds": None,  # Explicitly null
            "authors": [{"name": "Test Author"}],
        }
        
        client = SemanticScholarClient()
        result = client._parse_paper(data)
        
        assert result.doi is None
        assert result.arxiv_id is None


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self, mock_http_response):
        """Test handling of 429 rate limit errors."""
        from src.services.semantic_scholar import SemanticScholarClient, SemanticScholarError
        
        mock_response = mock_http_response(status_code=429)
        mock_response.text = "Too Many Requests"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            client = SemanticScholarClient()
            client._client = mock_client
            
            with pytest.raises(SemanticScholarError) as exc_info:
                await client.search("test")
            
            assert exc_info.value.status_code == 429
            assert "Rate limit" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_not_found_error(self, mock_http_response):
        """Test handling of 404 not found errors."""
        from src.services.semantic_scholar import SemanticScholarClient, SemanticScholarError
        
        mock_response = mock_http_response(status_code=404)
        mock_response.text = "Paper not found"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            client = SemanticScholarClient()
            client._client = mock_client
            
            with pytest.raises(SemanticScholarError) as exc_info:
                await client.get_paper("nonexistent")
            
            assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    async def test_client_not_initialized_error(self):
        """Test error when client is used without context manager."""
        from src.services.semantic_scholar import SemanticScholarClient, SemanticScholarError
        
        client = SemanticScholarClient()
        # Don't use async with
        
        with pytest.raises(SemanticScholarError) as exc_info:
            await client.search("test")
        
        assert "not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_server_error(self, mock_http_response):
        """Test handling of 500 server errors."""
        from src.services.semantic_scholar import SemanticScholarClient, SemanticScholarError
        
        mock_response = mock_http_response(status_code=500)
        mock_response.text = "Internal Server Error"
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            client = SemanticScholarClient()
            client._client = mock_client
            
            with pytest.raises(SemanticScholarError) as exc_info:
                await client.search("test")
            
            assert exc_info.value.status_code == 500


class TestApiKeyHandling:
    """Test API key handling."""
    
    def test_api_key_constructor(self):
        """Test that API key is stored from constructor."""
        from src.services.semantic_scholar import SemanticScholarClient
        
        # Test that API key constructor arg is stored
        client = SemanticScholarClient(api_key="test-api-key")
        assert client.api_key == "test-api-key"
    
    def test_api_key_default_from_settings(self, mock_env):
        """Test that API key defaults from settings."""
        from src.services.semantic_scholar import SemanticScholarClient
        
        with patch("src.services.semantic_scholar.get_settings") as mock_settings:
            mock_settings.return_value.semantic_scholar_api_key = "settings-api-key"
            client = SemanticScholarClient()
            assert client.api_key == "settings-api-key"


class TestSpecialLookups:
    """Test paper lookup by DOI and arXiv ID."""
    
    @pytest.mark.asyncio
    async def test_get_paper_by_doi(self, mock_http_response, sample_paper_data):
        """Test looking up paper by DOI."""
        from src.services.semantic_scholar import SemanticScholarClient
        
        mock_response = mock_http_response(
            status_code=200,
            json_data=sample_paper_data,
        )
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            client = SemanticScholarClient()
            client._client = mock_client
            
            result = await client.get_paper_by_doi("10.48550/arXiv.1706.03762")
            
            # Verify DOI prefix was added
            call_args = mock_client.get.call_args
            assert "DOI:10.48550/arXiv.1706.03762" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_get_paper_by_arxiv(self, mock_http_response, sample_paper_data):
        """Test looking up paper by arXiv ID."""
        from src.services.semantic_scholar import SemanticScholarClient
        
        mock_response = mock_http_response(
            status_code=200,
            json_data=sample_paper_data,
        )
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            client = SemanticScholarClient()
            client._client = mock_client
            
            result = await client.get_paper_by_arxiv("1706.03762")
            
            # Verify ARXIV prefix was added
            call_args = mock_client.get.call_args
            assert "ARXIV:1706.03762" in str(call_args)

