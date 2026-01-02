"""
CrossRef API Client.

CrossRef is a DOI registration agency with extensive metadata for scholarly works.

API Docs: https://api.crossref.org/swagger-ui/index.html
Rate limit: 50 requests/second with polite pool (email in User-Agent).
"""

import asyncio
import logging
from typing import Optional

import httpx

from src.models.source import Author, PaperSearchResult, PaperSearchResponse

logger = logging.getLogger(__name__)

CROSSREF_API_URL = "https://api.crossref.org"


class CrossRefError(Exception):
    """CrossRef API error."""
    pass


class CrossRefClient:
    """
    Client for CrossRef API.
    
    Free, no API key required.
    Add email to User-Agent for polite pool (higher rate limits).
    """
    
    def __init__(
        self,
        email: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize CrossRef client.
        
        Args:
            email: Email for polite pool (recommended).
            timeout: Request timeout in seconds.
        """
        self.email = email or "academic-research-tool@example.com"
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> "CrossRefClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "User-Agent": f"academic-research-tool/1.0 (mailto:{self.email})",
                "Accept": "application/json",
            }
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
        limit: int = 25,
        offset: int = 0,
        sort: str = "relevance",  # relevance, published, indexed
        filter_type: Optional[str] = None,  # e.g., "journal-article", "book-chapter"
        from_pub_date: Optional[str] = None,  # YYYY-MM-DD format
        until_pub_date: Optional[str] = None,
    ) -> PaperSearchResponse:
        """
        Search CrossRef for works.
        
        Args:
            query: Search query.
            limit: Max results per request (max 1000).
            offset: Starting index.
            sort: Sort field.
            filter_type: Filter by work type.
            from_pub_date: Minimum publication date.
            until_pub_date: Maximum publication date.
        
        Returns:
            PaperSearchResponse with results.
        """
        if not self._client:
            raise CrossRefError("Client not initialized. Use async context manager.")
        
        params = {
            "query": query,
            "rows": min(limit, 1000),
            "offset": offset,
            "sort": sort,
            "order": "desc" if sort == "relevance" else "asc",
        }
        
        # Build filter string
        filters = []
        if filter_type:
            filters.append(f"type:{filter_type}")
        if from_pub_date:
            filters.append(f"from-pub-date:{from_pub_date}")
        if until_pub_date:
            filters.append(f"until-pub-date:{until_pub_date}")
        
        if filters:
            params["filter"] = ",".join(filters)
        
        try:
            response = await self._client.get(
                f"{CROSSREF_API_URL}/works",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            
            message = data.get("message", {})
            total = message.get("total-results", 0)
            items = message.get("items", [])
            
            papers = []
            for item in items:
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
            logger.error(f"CrossRef API error: {e.response.status_code}")
            raise CrossRefError(f"API error: {e.response.status_code}")
        except httpx.HTTPError as e:
            logger.error(f"CrossRef request failed: {e}")
            raise CrossRefError(f"Request failed: {e}")
    
    async def get_paper(self, doi: str) -> Optional[PaperSearchResult]:
        """
        Get a paper by DOI.
        
        Args:
            doi: DOI (e.g., "10.1038/nature12373").
        
        Returns:
            Paper details or None.
        """
        if not self._client:
            raise CrossRefError("Client not initialized. Use async context manager.")
        
        # Clean DOI
        clean_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        
        try:
            response = await self._client.get(f"{CROSSREF_API_URL}/works/{clean_doi}")
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            data = response.json()
            
            return self._parse_work(data.get("message", {}))
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get CrossRef paper: {e}")
            return None
    
    async def get_references(
        self,
        doi: str,
        limit: int = 100,
    ) -> list[PaperSearchResult]:
        """
        Get papers referenced by a DOI.
        
        Args:
            doi: DOI of the citing paper.
            limit: Max references to return.
        
        Returns:
            List of referenced papers.
        """
        if not self._client:
            raise CrossRefError("Client not initialized. Use async context manager.")
        
        clean_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        
        try:
            response = await self._client.get(f"{CROSSREF_API_URL}/works/{clean_doi}")
            
            if response.status_code == 404:
                return []
            
            response.raise_for_status()
            data = response.json()
            
            references = data.get("message", {}).get("reference", [])
            
            # References have limited info, fetch full details where DOI available
            papers = []
            for ref in references[:limit]:
                ref_doi = ref.get("DOI")
                if ref_doi:
                    paper = await self.get_paper(ref_doi)
                    if paper:
                        papers.append(paper)
                else:
                    # Create minimal paper from reference data
                    papers.append(PaperSearchResult(
                        paper_id=f"crossref:ref:{ref.get('key', 'unknown')}",
                        doi=None,
                        arxiv_id=None,
                        title=ref.get("article-title") or ref.get("unstructured", "Unknown"),
                        authors=[Author(name=ref.get("author", "Unknown"))],
                        abstract=None,
                        publication_year=ref.get("year"),
                        venue=ref.get("journal-title"),
                        is_open_access=False,
                        pdf_url=None,
                        citation_count=None,
                        reference_count=None,
                        source_api="crossref",
                    ))
            
            return papers
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get references: {e}")
            return []
    
    def _parse_work(self, work: dict) -> Optional[PaperSearchResult]:
        """Parse a CrossRef work into PaperSearchResult."""
        if not work:
            return None
        
        try:
            doi = work.get("DOI")
            
            # Title (can be a list)
            titles = work.get("title", [])
            title = titles[0] if titles else "Untitled"
            
            # Authors
            authors = []
            for author in work.get("author", []):
                name_parts = []
                if author.get("given"):
                    name_parts.append(author["given"])
                if author.get("family"):
                    name_parts.append(author["family"])
                
                if name_parts:
                    # ORCID
                    orcid = author.get("ORCID")
                    if orcid:
                        orcid = orcid.replace("http://orcid.org/", "")
                    
                    # Affiliation
                    affiliations = author.get("affiliation", [])
                    affiliation = affiliations[0].get("name") if affiliations else None
                    
                    authors.append(Author(
                        name=" ".join(name_parts),
                        orcid=orcid,
                        affiliation=affiliation,
                    ))
            
            # Abstract
            abstract = work.get("abstract")
            if abstract:
                # CrossRef abstracts sometimes have XML tags
                abstract = abstract.replace("<jats:p>", "").replace("</jats:p>", "")
                abstract = abstract.replace("<jats:title>", "").replace("</jats:title>", "")
            
            # Publication year
            year = None
            published = work.get("published-print") or work.get("published-online") or work.get("created")
            if published:
                date_parts = published.get("date-parts", [[]])
                if date_parts and date_parts[0]:
                    year = date_parts[0][0]
            
            # Venue (journal/container)
            venue = None
            container = work.get("container-title", [])
            if container:
                venue = container[0]
            
            # Open access and PDF URL
            is_open_access = False
            pdf_url = None
            
            # Check license
            licenses = work.get("license", [])
            for lic in licenses:
                url = lic.get("URL", "")
                if "creativecommons" in url or "open" in url.lower():
                    is_open_access = True
                    break
            
            # Check for PDF link
            links = work.get("link", [])
            for link in links:
                if link.get("content-type") == "application/pdf":
                    pdf_url = link.get("URL")
                    break
            
            # Citation count
            citation_count = work.get("is-referenced-by-count")
            reference_count = work.get("references-count")
            
            return PaperSearchResult(
                paper_id=f"crossref:{doi}" if doi else f"crossref:{work.get('URL', 'unknown')}",
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
                reference_count=reference_count,
                source_api="crossref",
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse CrossRef work: {e}")
            return None


# Convenience function
async def search_crossref(
    query: str,
    limit: int = 25,
    **kwargs,
) -> PaperSearchResponse:
    """
    Search CrossRef for papers (convenience function).
    
    Args:
        query: Search query.
        limit: Max results.
        **kwargs: Additional search parameters.
    
    Returns:
        PaperSearchResponse with results.
    """
    async with CrossRefClient() as client:
        return await client.search(query, limit=limit, **kwargs)
