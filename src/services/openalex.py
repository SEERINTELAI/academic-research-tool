"""
OpenAlex API Client.

OpenAlex is a free, open catalog of academic papers.
No API key required, generous rate limits.

Docs: https://docs.openalex.org/
"""

import logging
from typing import Optional
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

OPENALEX_API_URL = "https://api.openalex.org"


class OpenAlexAuthor(BaseModel):
    """Author information."""
    name: str
    author_id: Optional[str] = None
    orcid: Optional[str] = None


class OpenAlexPaper(BaseModel):
    """Paper from OpenAlex."""
    paper_id: str
    title: str
    authors: list[OpenAlexAuthor] = Field(default_factory=list)
    abstract: Optional[str] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    citation_count: Optional[int] = None
    doi: Optional[str] = None
    pdf_url: Optional[str] = None
    open_access_url: Optional[str] = None
    external_ids: dict = Field(default_factory=dict)


class OpenAlexSearchResult(BaseModel):
    """Search results from OpenAlex."""
    results: list[OpenAlexPaper]
    total: int
    page: int
    per_page: int


class OpenAlexError(Exception):
    """OpenAlex API error."""
    pass


class OpenAlexClient:
    """
    Client for OpenAlex API.
    
    Free, no API key required.
    Polite pool: add email to get into faster queue.
    """
    
    def __init__(self, email: Optional[str] = None, timeout: float = 30.0):
        """
        Initialize OpenAlex client.
        
        Args:
            email: Optional email for polite pool (faster responses).
            timeout: Request timeout in seconds.
        """
        self.email = email or "academic-research-tool@example.com"
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> "OpenAlexClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={"User-Agent": f"academic-research-tool/1.0 (mailto:{self.email})"}
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
        page: int = 1,
        sort: str = "relevance_score:desc",
    ) -> OpenAlexSearchResult:
        """
        Search for papers.
        
        Args:
            query: Search query.
            limit: Max results per page (max 200).
            page: Page number (1-indexed).
            sort: Sort order.
        
        Returns:
            Search results.
        """
        if not self._client:
            raise OpenAlexError("Client not initialized. Use async context manager.")
        
        # Build search URL
        params = {
            "search": query,
            "per_page": min(limit, 200),
            "page": page,
            "mailto": self.email,
        }
        
        try:
            response = await self._client.get(
                f"{OPENALEX_API_URL}/works",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            
            # Parse results
            papers = []
            for work in data.get("results", []):
                paper = self._parse_work(work)
                if paper:
                    papers.append(paper)
            
            return OpenAlexSearchResult(
                results=papers,
                total=data.get("meta", {}).get("count", 0),
                page=page,
                per_page=limit,
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAlex API error: {e.response.status_code}")
            raise OpenAlexError(f"API error: {e.response.status_code}")
        except httpx.HTTPError as e:
            logger.error(f"OpenAlex request failed: {e}")
            raise OpenAlexError(f"Request failed: {e}")
    
    async def get_paper(self, paper_id: str) -> Optional[OpenAlexPaper]:
        """
        Get a paper by ID.
        
        Args:
            paper_id: OpenAlex ID (e.g., "W2741809807") or DOI.
        
        Returns:
            Paper details or None.
        """
        if not self._client:
            raise OpenAlexError("Client not initialized. Use async context manager.")
        
        # Handle DOI format
        if paper_id.startswith("10."):
            url = f"{OPENALEX_API_URL}/works/doi:{paper_id}"
        elif paper_id.startswith("https://doi.org/"):
            doi = paper_id.replace("https://doi.org/", "")
            url = f"{OPENALEX_API_URL}/works/doi:{doi}"
        else:
            url = f"{OPENALEX_API_URL}/works/{paper_id}"
        
        try:
            response = await self._client.get(url, params={"mailto": self.email})
            response.raise_for_status()
            return self._parse_work(response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise OpenAlexError(f"API error: {e.response.status_code}")
    
    async def get_cited_by(
        self,
        paper_id: str,
        limit: int = 25,
    ) -> list[OpenAlexPaper]:
        """
        Get papers that cite this paper.
        
        Args:
            paper_id: OpenAlex ID.
            limit: Max results.
        
        Returns:
            List of citing papers.
        """
        if not self._client:
            raise OpenAlexError("Client not initialized. Use async context manager.")
        
        try:
            response = await self._client.get(
                f"{OPENALEX_API_URL}/works",
                params={
                    "filter": f"cites:{paper_id}",
                    "per_page": min(limit, 200),
                    "mailto": self.email,
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                self._parse_work(work)
                for work in data.get("results", [])
                if self._parse_work(work)
            ]
        except httpx.HTTPError as e:
            logger.error(f"Failed to get citations: {e}")
            return []
    
    async def get_references(
        self,
        paper_id: str,
        limit: int = 25,
    ) -> list[OpenAlexPaper]:
        """
        Get papers referenced by this paper.
        
        Args:
            paper_id: OpenAlex ID.
            limit: Max results.
        
        Returns:
            List of referenced papers.
        """
        if not self._client:
            raise OpenAlexError("Client not initialized. Use async context manager.")
        
        try:
            # First get the paper to find its references
            paper = await self.get_paper(paper_id)
            if not paper:
                return []
            
            # OpenAlex stores reference IDs in the work object
            response = await self._client.get(
                f"{OPENALEX_API_URL}/works/{paper_id}",
                params={"mailto": self.email}
            )
            response.raise_for_status()
            data = response.json()
            
            ref_ids = data.get("referenced_works", [])[:limit]
            
            if not ref_ids:
                return []
            
            # Fetch referenced works
            # Use filter to get multiple works at once
            ids_filter = "|".join([r.split("/")[-1] for r in ref_ids])
            
            response = await self._client.get(
                f"{OPENALEX_API_URL}/works",
                params={
                    "filter": f"openalex_id:{ids_filter}",
                    "per_page": limit,
                    "mailto": self.email,
                }
            )
            response.raise_for_status()
            
            return [
                self._parse_work(work)
                for work in response.json().get("results", [])
                if self._parse_work(work)
            ]
        except httpx.HTTPError as e:
            logger.error(f"Failed to get references: {e}")
            return []
    
    def _parse_work(self, work: dict) -> Optional[OpenAlexPaper]:
        """Parse OpenAlex work into Paper model."""
        if not work:
            return None
        
        try:
            # Extract authors
            authors = []
            for authorship in work.get("authorships", []):
                author_data = authorship.get("author", {})
                if author_data:
                    authors.append(OpenAlexAuthor(
                        name=author_data.get("display_name", "Unknown"),
                        author_id=author_data.get("id"),
                        orcid=author_data.get("orcid"),
                    ))
            
            # Extract abstract (OpenAlex stores inverted index)
            abstract = None
            abstract_index = work.get("abstract_inverted_index")
            if abstract_index:
                abstract = self._reconstruct_abstract(abstract_index)
            
            # Get PDF URL from open access
            pdf_url = None
            oa_url = None
            oa = work.get("open_access", {})
            if oa.get("is_oa"):
                oa_url = oa.get("oa_url")
                # Check best_oa_location for PDF
                best_loc = work.get("best_oa_location", {})
                if best_loc:
                    pdf_url = best_loc.get("pdf_url")
                    if not oa_url:
                        oa_url = best_loc.get("landing_page_url")
            
            # Get venue
            venue = None
            primary_location = work.get("primary_location", {})
            if primary_location:
                source = primary_location.get("source", {})
                if source:
                    venue = source.get("display_name")
            
            # External IDs
            external_ids = {}
            ids = work.get("ids", {})
            if ids.get("doi"):
                external_ids["doi"] = ids["doi"].replace("https://doi.org/", "")
            if ids.get("pmid"):
                external_ids["pmid"] = ids["pmid"]
            if ids.get("mag"):
                external_ids["mag"] = str(ids["mag"])
            
            return OpenAlexPaper(
                paper_id=work.get("id", "").split("/")[-1],
                title=work.get("title") or "Untitled",
                authors=authors,
                abstract=abstract,
                year=work.get("publication_year"),
                venue=venue,
                citation_count=work.get("cited_by_count"),
                doi=external_ids.get("doi"),
                pdf_url=pdf_url,
                open_access_url=oa_url,
                external_ids=external_ids,
            )
        except Exception as e:
            logger.warning(f"Failed to parse work: {e}")
            return None
    
    def _reconstruct_abstract(self, inverted_index: dict) -> str:
        """Reconstruct abstract from OpenAlex inverted index format."""
        if not inverted_index:
            return ""
        
        # Inverted index: {"word": [positions]}
        words = []
        for word, positions in inverted_index.items():
            for pos in positions:
                words.append((pos, word))
        
        # Sort by position and join
        words.sort(key=lambda x: x[0])
        return " ".join(w[1] for w in words)

