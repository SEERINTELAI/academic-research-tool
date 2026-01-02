"""
arXiv API Client.

arXiv is an open-access repository for scholarly articles in physics,
mathematics, computer science, and related fields.

API Docs: https://info.arxiv.org/help/api/index.html
Rate limit: 1 request per 3 seconds (no API key needed)
"""

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from typing import Optional
from urllib.parse import urlencode

import httpx

from src.models.source import Author, PaperSearchResult, PaperSearchResponse

logger = logging.getLogger(__name__)

ARXIV_API_URL = "http://export.arxiv.org/api/query"

# XML namespaces used in arXiv API responses
NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


class ArxivError(Exception):
    """arXiv API error."""
    pass


class ArxivClient:
    """
    Client for arXiv API.
    
    Free, no API key required.
    Rate limit: 1 request per 3 seconds (enforced by client).
    """
    
    def __init__(self, timeout: float = 30.0):
        """
        Initialize arXiv client.
        
        Args:
            timeout: Request timeout in seconds.
        """
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._last_request_time: float = 0.0
    
    async def __aenter__(self) -> "ArxivClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={"User-Agent": "academic-research-tool/1.0"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _rate_limit(self) -> None:
        """Enforce rate limiting (1 request per 3 seconds)."""
        import time
        elapsed = time.time() - self._last_request_time
        if elapsed < 3.0:
            await asyncio.sleep(3.0 - elapsed)
        self._last_request_time = time.time()
    
    async def search(
        self,
        query: str,
        limit: int = 25,
        offset: int = 0,
        sort_by: str = "relevance",  # relevance, lastUpdatedDate, submittedDate
        sort_order: str = "descending",
    ) -> PaperSearchResponse:
        """
        Search for papers on arXiv.
        
        Args:
            query: Search query (supports arXiv query syntax).
            limit: Max results per request (max 2000).
            offset: Starting index for results.
            sort_by: Sort field.
            sort_order: ascending or descending.
        
        Returns:
            PaperSearchResponse with results.
        """
        if not self._client:
            raise ArxivError("Client not initialized. Use async context manager.")
        
        await self._rate_limit()
        
        # Build search query
        # arXiv uses a specific query syntax: all:query, ti:title, au:author, etc.
        # For general search, use "all:"
        search_query = query if ":" in query else f"all:{query}"
        
        params = {
            "search_query": search_query,
            "start": offset,
            "max_results": min(limit, 2000),
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
        
        try:
            response = await self._client.get(ARXIV_API_URL, params=params)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.text)
            
            # Get total results from opensearch:totalResults
            total_elem = root.find(".//{http://a9.com/-/spec/opensearch/1.1/}totalResults")
            total = int(total_elem.text) if total_elem is not None else 0
            
            # Parse entries
            papers = []
            for entry in root.findall("atom:entry", NAMESPACES):
                paper = self._parse_entry(entry)
                if paper:
                    papers.append(paper)
            
            return PaperSearchResponse(
                query=query,
                total_results=total,
                results=papers,
                next_offset=offset + len(papers) if len(papers) == limit else None,
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"arXiv API error: {e.response.status_code}")
            raise ArxivError(f"API error: {e.response.status_code}")
        except ET.ParseError as e:
            logger.error(f"Failed to parse arXiv response: {e}")
            raise ArxivError(f"Parse error: {e}")
        except httpx.HTTPError as e:
            logger.error(f"arXiv request failed: {e}")
            raise ArxivError(f"Request failed: {e}")
    
    async def get_paper(self, arxiv_id: str) -> Optional[PaperSearchResult]:
        """
        Get a paper by arXiv ID.
        
        Args:
            arxiv_id: arXiv ID (e.g., "2103.00020" or "2103.00020v1").
        
        Returns:
            Paper details or None.
        """
        if not self._client:
            raise ArxivError("Client not initialized. Use async context manager.")
        
        await self._rate_limit()
        
        # Clean up arxiv ID
        clean_id = arxiv_id.replace("arXiv:", "").replace("arxiv:", "")
        
        params = {"id_list": clean_id}
        
        try:
            response = await self._client.get(ARXIV_API_URL, params=params)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            entries = root.findall("atom:entry", NAMESPACES)
            
            if not entries:
                return None
            
            return self._parse_entry(entries[0])
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get arXiv paper: {e}")
            return None
    
    def _parse_entry(self, entry: ET.Element) -> Optional[PaperSearchResult]:
        """Parse an arXiv Atom entry into PaperSearchResult."""
        try:
            # Get arXiv ID from the id element
            id_elem = entry.find("atom:id", NAMESPACES)
            if id_elem is None:
                return None
            
            # ID format: http://arxiv.org/abs/2103.00020v1
            arxiv_url = id_elem.text or ""
            arxiv_id = arxiv_url.split("/abs/")[-1] if "/abs/" in arxiv_url else ""
            
            # Extract version-less ID for paper_id
            paper_id = re.sub(r"v\d+$", "", arxiv_id)
            
            # Get title
            title_elem = entry.find("atom:title", NAMESPACES)
            title = (title_elem.text or "Untitled").strip().replace("\n", " ")
            
            # Get abstract
            summary_elem = entry.find("atom:summary", NAMESPACES)
            abstract = (summary_elem.text or "").strip().replace("\n", " ") if summary_elem is not None else None
            
            # Get authors
            authors = []
            for author_elem in entry.findall("atom:author", NAMESPACES):
                name_elem = author_elem.find("atom:name", NAMESPACES)
                if name_elem is not None and name_elem.text:
                    affil_elem = author_elem.find("arxiv:affiliation", NAMESPACES)
                    authors.append(Author(
                        name=name_elem.text,
                        affiliation=affil_elem.text if affil_elem is not None else None,
                    ))
            
            # Get publication date
            published_elem = entry.find("atom:published", NAMESPACES)
            year = None
            if published_elem is not None and published_elem.text:
                # Format: 2021-03-01T00:00:00Z
                year = int(published_elem.text[:4])
            
            # Get category (venue)
            primary_category = entry.find("arxiv:primary_category", NAMESPACES)
            venue = None
            if primary_category is not None:
                venue = f"arXiv:{primary_category.get('term', '')}"
            
            # Get PDF URL
            pdf_url = None
            for link in entry.findall("atom:link", NAMESPACES):
                if link.get("title") == "pdf":
                    pdf_url = link.get("href")
                    break
            
            # Get DOI if available
            doi = None
            doi_elem = entry.find("arxiv:doi", NAMESPACES)
            if doi_elem is not None:
                doi = doi_elem.text
            
            return PaperSearchResult(
                paper_id=f"arxiv:{paper_id}",
                doi=doi,
                arxiv_id=arxiv_id,
                title=title,
                authors=authors,
                abstract=abstract,
                publication_year=year,
                venue=venue,
                is_open_access=True,  # arXiv papers are always open access
                pdf_url=pdf_url,
                citation_count=None,  # arXiv doesn't provide citation counts
                reference_count=None,
                source_api="arxiv",
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse arXiv entry: {e}")
            return None


# Convenience function
async def search_arxiv(
    query: str,
    limit: int = 25,
    **kwargs,
) -> PaperSearchResponse:
    """
    Search arXiv for papers (convenience function).
    
    Args:
        query: Search query.
        limit: Max results.
        **kwargs: Additional search parameters.
    
    Returns:
        PaperSearchResponse with results.
    """
    async with ArxivClient() as client:
        return await client.search(query, limit=limit, **kwargs)
