"""
Semantic Scholar API Client.

Client for searching and retrieving academic paper metadata.
API Documentation: https://api.semanticscholar.org/api-docs/
"""

import asyncio
import logging
from typing import Optional

import httpx

from src.config import get_settings
from src.models.source import (
    Author,
    PaperSearchResult,
    PaperSearchRequest,
    PaperSearchResponse,
)

logger = logging.getLogger(__name__)

# Semantic Scholar API endpoints
BASE_URL = "https://api.semanticscholar.org/graph/v1"

# Fields to request from the API
PAPER_FIELDS = [
    "paperId",
    "externalIds",
    "title",
    "abstract",
    "venue",
    "year",
    "authors",
    "citationCount",
    "referenceCount",
    "isOpenAccess",
    "openAccessPdf",
    "fieldsOfStudy",
]


class SemanticScholarError(Exception):
    """Semantic Scholar API error."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class SemanticScholarClient:
    """
    Client for Semantic Scholar API.
    
    Rate limits:
    - Without API key: 100 requests per 5 minutes
    - With API key: Higher limits (contact S2 for details)
    
    Usage:
        async with SemanticScholarClient() as client:
            results = await client.search("machine learning")
    """
    
    def __init__(self, api_key: Optional[str] = None, timeout: float = 30.0):
        """
        Initialize Semantic Scholar client.
        
        Args:
            api_key: Optional API key for higher rate limits.
            timeout: Request timeout in seconds.
        """
        settings = get_settings()
        self.api_key = api_key or settings.semantic_scholar_api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> "SemanticScholarClient":
        """Async context manager entry."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers=headers,
            timeout=self.timeout,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        open_access_only: bool = False,
        fields_of_study: Optional[list[str]] = None,
    ) -> PaperSearchResponse:
        """
        Search for papers by keyword.
        
        Args:
            query: Search query string.
            limit: Maximum results to return (1-100).
            offset: Pagination offset.
            year_from: Filter papers from this year.
            year_to: Filter papers to this year.
            open_access_only: Only return open access papers.
            fields_of_study: Filter by fields (e.g., ["Computer Science"]).
        
        Returns:
            PaperSearchResponse with results.
        
        Raises:
            SemanticScholarError: If API request fails.
        """
        if not self._client:
            raise SemanticScholarError("Client not initialized. Use async context manager.")
        
        # Build query parameters
        params = {
            "query": query,
            "limit": min(limit, 100),
            "offset": offset,
            "fields": ",".join(PAPER_FIELDS),
        }
        
        # Add year filter
        if year_from or year_to:
            year_filter = ""
            if year_from and year_to:
                year_filter = f"{year_from}-{year_to}"
            elif year_from:
                year_filter = f"{year_from}-"
            elif year_to:
                year_filter = f"-{year_to}"
            params["year"] = year_filter
        
        # Add open access filter
        if open_access_only:
            params["openAccessPdf"] = ""  # Filter for papers with OA PDF
        
        # Add fields of study filter
        if fields_of_study:
            params["fieldsOfStudy"] = ",".join(fields_of_study)
        
        try:
            response = await self._client.get("/paper/search", params=params)
            
            if response.status_code == 429:
                raise SemanticScholarError("Rate limit exceeded. Try again later.", 429)
            
            if response.status_code != 200:
                raise SemanticScholarError(
                    f"API error: {response.text}", 
                    response.status_code
                )
            
            data = response.json()
            
            # Parse results
            results = []
            for paper in data.get("data", []):
                result = self._parse_paper(paper)
                
                # Apply open access filter (API doesn't always filter correctly)
                if open_access_only and not result.is_open_access:
                    continue
                
                results.append(result)
            
            return PaperSearchResponse(
                query=query,
                total_results=data.get("total", len(results)),
                results=results,
                next_offset=offset + len(results) if len(results) == limit else None,
            )
            
        except httpx.HTTPError as e:
            logger.exception(f"HTTP error searching papers: {e}")
            raise SemanticScholarError(f"HTTP error: {e}")
    
    async def get_paper(self, paper_id: str) -> PaperSearchResult:
        """
        Get details for a specific paper.
        
        Args:
            paper_id: Semantic Scholar paper ID, DOI, or arXiv ID.
                      Prefix DOI with "DOI:" and arXiv with "ARXIV:".
        
        Returns:
            PaperSearchResult with paper details.
        """
        if not self._client:
            raise SemanticScholarError("Client not initialized. Use async context manager.")
        
        try:
            response = await self._client.get(
                f"/paper/{paper_id}",
                params={"fields": ",".join(PAPER_FIELDS)},
            )
            
            if response.status_code == 404:
                raise SemanticScholarError(f"Paper not found: {paper_id}", 404)
            
            if response.status_code != 200:
                raise SemanticScholarError(
                    f"API error: {response.text}",
                    response.status_code
                )
            
            return self._parse_paper(response.json())
            
        except httpx.HTTPError as e:
            logger.exception(f"HTTP error getting paper: {e}")
            raise SemanticScholarError(f"HTTP error: {e}")
    
    async def get_paper_by_doi(self, doi: str) -> PaperSearchResult:
        """Get paper by DOI."""
        return await self.get_paper(f"DOI:{doi}")
    
    async def get_paper_by_arxiv(self, arxiv_id: str) -> PaperSearchResult:
        """Get paper by arXiv ID."""
        return await self.get_paper(f"ARXIV:{arxiv_id}")
    
    def _parse_paper(self, data: dict) -> PaperSearchResult:
        """
        Parse API response into PaperSearchResult.
        
        Args:
            data: Raw paper data from API.
        
        Returns:
            Parsed PaperSearchResult.
        """
        # Extract external IDs
        external_ids = data.get("externalIds") or {}
        
        # Parse authors
        authors = []
        for author_data in data.get("authors", []):
            authors.append(Author(
                name=author_data.get("name", "Unknown"),
                author_id=author_data.get("authorId"),
            ))
        
        # Get open access PDF URL
        oa_pdf = data.get("openAccessPdf") or {}
        pdf_url = oa_pdf.get("url")
        
        return PaperSearchResult(
            paper_id=data.get("paperId", ""),
            doi=external_ids.get("DOI"),
            arxiv_id=external_ids.get("ArXiv"),
            title=data.get("title", "Untitled"),
            authors=authors,
            abstract=data.get("abstract"),
            publication_year=data.get("year"),
            venue=data.get("venue"),
            is_open_access=data.get("isOpenAccess", False),
            pdf_url=pdf_url,
            citation_count=data.get("citationCount"),
            reference_count=data.get("referenceCount"),
            source_api="semantic_scholar",
        )


# Convenience function
async def search_papers(
    query: str,
    limit: int = 20,
    **kwargs,
) -> PaperSearchResponse:
    """
    Search for papers (convenience function).
    
    Args:
        query: Search query.
        limit: Max results.
        **kwargs: Additional search parameters.
    
    Returns:
        PaperSearchResponse with results.
    """
    async with SemanticScholarClient() as client:
        return await client.search(query, limit=limit, **kwargs)

