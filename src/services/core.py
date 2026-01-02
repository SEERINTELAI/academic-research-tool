"""
CORE API Client.

CORE is the world's largest collection of open access research papers.

API Docs: https://core.ac.uk/documentation/api
Rate limit: Free tier has rate limits; API key available for higher limits.
"""

import asyncio
import logging
from typing import Optional

import httpx

from src.models.source import Author, PaperSearchResult, PaperSearchResponse

logger = logging.getLogger(__name__)

CORE_API_URL = "https://api.core.ac.uk/v3"


class CoreError(Exception):
    """CORE API error."""
    pass


class CoreClient:
    """
    Client for CORE API.
    
    Free tier available, API key recommended for production use.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize CORE client.
        
        Args:
            api_key: CORE API key (get from https://core.ac.uk/services/api).
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._last_request_time: float = 0.0
    
    async def __aenter__(self) -> "CoreClient":
        """Async context manager entry."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "academic-research-tool/1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers=headers,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _rate_limit(self) -> None:
        """Enforce rate limiting (conservative without API key)."""
        import time
        # Without API key, be conservative: 1 request per second
        min_interval = 0.2 if self.api_key else 1.0
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request_time = time.time()
    
    async def search(
        self,
        query: str,
        limit: int = 25,
        offset: int = 0,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        language: Optional[str] = None,
    ) -> PaperSearchResponse:
        """
        Search CORE for papers.
        
        Args:
            query: Search query.
            limit: Max results (max 100 per request).
            offset: Starting index.
            year_from: Minimum publication year.
            year_to: Maximum publication year.
            language: Language filter (ISO 639-1 code).
        
        Returns:
            PaperSearchResponse with results.
        """
        if not self._client:
            raise CoreError("Client not initialized. Use async context manager.")
        
        await self._rate_limit()
        
        # Build search request body
        body = {
            "q": query,
            "limit": min(limit, 100),
            "offset": offset,
        }
        
        # Build filters
        filters = []
        if year_from:
            filters.append(f"yearPublished>={year_from}")
        if year_to:
            filters.append(f"yearPublished<={year_to}")
        if language:
            filters.append(f"language={language}")
        
        if filters:
            body["filters"] = filters
        
        try:
            response = await self._client.post(
                f"{CORE_API_URL}/search/works",
                json=body,
            )
            
            if response.status_code == 401:
                raise CoreError("Unauthorized. API key may be invalid or required.")
            
            if response.status_code == 429:
                raise CoreError("Rate limit exceeded. Try again later or use API key.")
            
            response.raise_for_status()
            data = response.json()
            
            total = data.get("totalHits", 0)
            results = data.get("results", [])
            
            papers = []
            for item in results:
                paper = self._parse_work(item)
                if paper:
                    papers.append(paper)
            
            return PaperSearchResponse(
                query=query,
                total_results=total,
                results=papers,
                next_offset=offset + len(papers) if len(papers) == limit else None,
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"CORE API error: {e.response.status_code}")
            raise CoreError(f"API error: {e.response.status_code}")
        except httpx.HTTPError as e:
            logger.error(f"CORE request failed: {e}")
            raise CoreError(f"Request failed: {e}")
    
    async def get_paper(self, core_id: str) -> Optional[PaperSearchResult]:
        """
        Get a paper by CORE ID.
        
        Args:
            core_id: CORE internal ID.
        
        Returns:
            Paper details or None.
        """
        if not self._client:
            raise CoreError("Client not initialized. Use async context manager.")
        
        await self._rate_limit()
        
        try:
            response = await self._client.get(f"{CORE_API_URL}/works/{core_id}")
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            return self._parse_work(response.json())
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get CORE paper: {e}")
            return None
    
    async def get_paper_by_doi(self, doi: str) -> Optional[PaperSearchResult]:
        """
        Get a paper by DOI.
        
        Args:
            doi: DOI string.
        
        Returns:
            Paper details or None.
        """
        # Search by DOI
        result = await self.search(f'doi:"{doi}"', limit=1)
        return result.results[0] if result.results else None
    
    def _parse_work(self, work: dict) -> Optional[PaperSearchResult]:
        """Parse a CORE work into PaperSearchResult."""
        if not work:
            return None
        
        try:
            core_id = work.get("id")
            
            # Title
            title = work.get("title") or "Untitled"
            
            # Abstract
            abstract = work.get("abstract")
            
            # Authors
            authors = []
            for author_name in work.get("authors", []):
                if isinstance(author_name, dict):
                    name = author_name.get("name", "Unknown")
                else:
                    name = str(author_name)
                authors.append(Author(name=name))
            
            # Year
            year = work.get("yearPublished")
            
            # DOI
            doi = work.get("doi")
            
            # Venue
            venue = None
            journals = work.get("journals", [])
            if journals:
                venue = journals[0].get("title") if isinstance(journals[0], dict) else str(journals[0])
            
            # PDF URL
            pdf_url = None
            download_url = work.get("downloadUrl")
            if download_url:
                pdf_url = download_url
            else:
                # Check fullText URL
                full_text_urls = work.get("fullTextUrls", [])
                if full_text_urls:
                    pdf_url = full_text_urls[0]
            
            # CORE papers are all open access
            is_open_access = True
            
            # Citation count (if available)
            citation_count = work.get("citationCount")
            
            return PaperSearchResult(
                paper_id=f"core:{core_id}" if core_id else "core:unknown",
                doi=doi,
                arxiv_id=None,
                title=title,
                authors=authors,
                abstract=abstract,
                publication_year=year,
                venue=venue,
                is_open_access=is_open_access,
                pdf_url=pdf_url,
                citation_count=citation_count,
                reference_count=None,
                source_api="core",
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse CORE work: {e}")
            return None


# Convenience function
async def search_core(
    query: str,
    limit: int = 25,
    **kwargs,
) -> PaperSearchResponse:
    """
    Search CORE for papers (convenience function).
    
    Args:
        query: Search query.
        limit: Max results.
        **kwargs: Additional search parameters.
    
    Returns:
        PaperSearchResponse with results.
    """
    async with CoreClient() as client:
        return await client.search(query, limit=limit, **kwargs)
