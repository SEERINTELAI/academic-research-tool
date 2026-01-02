"""
PubMed API Client (NCBI E-utilities).

PubMed is a free database of biomedical and life sciences literature.

API Docs: https://www.ncbi.nlm.nih.gov/books/NBK25500/
Rate limit: 3 requests/second without API key, 10 requests/second with key.
"""

import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import Optional

import httpx

from src.models.source import Author, PaperSearchResult, PaperSearchResponse

logger = logging.getLogger(__name__)

# NCBI E-utilities endpoints
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


class PubMedError(Exception):
    """PubMed API error."""
    pass


class PubMedClient:
    """
    Client for PubMed API (NCBI E-utilities).
    
    Free, API key optional but recommended for higher rate limits.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        email: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize PubMed client.
        
        Args:
            api_key: Optional NCBI API key for higher rate limits.
            email: Required by NCBI TOS for identification.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key
        self.email = email or "academic-research-tool@example.com"
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._last_request_time: float = 0.0
    
    async def __aenter__(self) -> "PubMedClient":
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
    
    async def _rate_limit(self) -> None:
        """Enforce rate limiting."""
        import time
        # Without API key: 3 requests/second, with key: 10 requests/second
        min_interval = 0.1 if self.api_key else 0.34
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request_time = time.time()
    
    def _base_params(self) -> dict:
        """Get base parameters for all requests."""
        params = {"tool": "academic-research-tool", "email": self.email}
        if self.api_key:
            params["api_key"] = self.api_key
        return params
    
    async def search(
        self,
        query: str,
        limit: int = 25,
        offset: int = 0,
        sort: str = "relevance",  # relevance, pub_date, author, title
        min_date: Optional[str] = None,  # YYYY/MM/DD format
        max_date: Optional[str] = None,
    ) -> PaperSearchResponse:
        """
        Search PubMed for papers.
        
        Args:
            query: Search query (supports PubMed query syntax).
            limit: Max results per request.
            offset: Starting index.
            sort: Sort order.
            min_date: Minimum publication date.
            max_date: Maximum publication date.
        
        Returns:
            PaperSearchResponse with results.
        """
        if not self._client:
            raise PubMedError("Client not initialized. Use async context manager.")
        
        await self._rate_limit()
        
        # Step 1: Use ESearch to get PMIDs
        search_params = {
            **self._base_params(),
            "db": "pubmed",
            "term": query,
            "retstart": offset,
            "retmax": min(limit, 10000),
            "retmode": "json",
            "sort": sort,
            "usehistory": "n",
        }
        
        if min_date:
            search_params["mindate"] = min_date
            search_params["datetype"] = "pdat"
        if max_date:
            search_params["maxdate"] = max_date
            search_params["datetype"] = "pdat"
        
        try:
            response = await self._client.get(ESEARCH_URL, params=search_params)
            response.raise_for_status()
            data = response.json()
            
            result = data.get("esearchresult", {})
            pmids = result.get("idlist", [])
            total = int(result.get("count", 0))
            
            if not pmids:
                return PaperSearchResponse(
                    query=query,
                    total_results=total,
                    results=[],
                    next_offset=None,
                )
            
            # Step 2: Use EFetch to get paper details
            await self._rate_limit()
            papers = await self._fetch_papers(pmids)
            
            return PaperSearchResponse(
                query=query,
                total_results=total,
                results=papers,
                next_offset=offset + len(papers) if len(papers) == limit else None,
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"PubMed API error: {e.response.status_code}")
            raise PubMedError(f"API error: {e.response.status_code}")
        except httpx.HTTPError as e:
            logger.error(f"PubMed request failed: {e}")
            raise PubMedError(f"Request failed: {e}")
    
    async def get_paper(self, pmid: str) -> Optional[PaperSearchResult]:
        """
        Get a paper by PubMed ID (PMID).
        
        Args:
            pmid: PubMed ID.
        
        Returns:
            Paper details or None.
        """
        if not self._client:
            raise PubMedError("Client not initialized. Use async context manager.")
        
        await self._rate_limit()
        
        papers = await self._fetch_papers([pmid])
        return papers[0] if papers else None
    
    async def _fetch_papers(self, pmids: list[str]) -> list[PaperSearchResult]:
        """Fetch paper details for a list of PMIDs."""
        if not pmids:
            return []
        
        fetch_params = {
            **self._base_params(),
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract",
        }
        
        try:
            response = await self._client.get(EFETCH_URL, params=fetch_params)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            papers = []
            
            for article in root.findall(".//PubmedArticle"):
                paper = self._parse_article(article)
                if paper:
                    papers.append(paper)
            
            return papers
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch PubMed papers: {e}")
            return []
        except ET.ParseError as e:
            logger.error(f"Failed to parse PubMed response: {e}")
            return []
    
    def _parse_article(self, article: ET.Element) -> Optional[PaperSearchResult]:
        """Parse a PubmedArticle XML element."""
        try:
            medline = article.find(".//MedlineCitation")
            if medline is None:
                return None
            
            # Get PMID
            pmid_elem = medline.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else None
            if not pmid:
                return None
            
            # Get article info
            article_elem = medline.find(".//Article")
            if article_elem is None:
                return None
            
            # Title
            title_elem = article_elem.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None else "Untitled"
            
            # Abstract
            abstract_parts = []
            for abstract_text in article_elem.findall(".//AbstractText"):
                label = abstract_text.get("Label", "")
                text = abstract_text.text or ""
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
            abstract = " ".join(abstract_parts) if abstract_parts else None
            
            # Authors
            authors = []
            for author_elem in article_elem.findall(".//Author"):
                last_name = author_elem.find("LastName")
                first_name = author_elem.find("ForeName")
                if last_name is not None and last_name.text:
                    name = last_name.text
                    if first_name is not None and first_name.text:
                        name = f"{first_name.text} {name}"
                    
                    # Get affiliation
                    affil_elem = author_elem.find(".//Affiliation")
                    affiliation = affil_elem.text if affil_elem is not None else None
                    
                    authors.append(Author(
                        name=name,
                        affiliation=affiliation,
                    ))
            
            # Publication year
            year = None
            pub_date = article_elem.find(".//PubDate")
            if pub_date is not None:
                year_elem = pub_date.find("Year")
                if year_elem is not None and year_elem.text:
                    try:
                        year = int(year_elem.text)
                    except ValueError:
                        pass
            
            # Journal (venue)
            venue = None
            journal = article_elem.find(".//Journal/Title")
            if journal is not None:
                venue = journal.text
            
            # DOI
            doi = None
            article_ids = article.findall(".//ArticleId")
            for aid in article_ids:
                if aid.get("IdType") == "doi":
                    doi = aid.text
                    break
            
            # PMC ID for PDF link
            pmc_id = None
            for aid in article_ids:
                if aid.get("IdType") == "pmc":
                    pmc_id = aid.text
                    break
            
            pdf_url = None
            if pmc_id:
                pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/"
            
            return PaperSearchResult(
                paper_id=f"pmid:{pmid}",
                doi=doi,
                arxiv_id=None,
                title=title,
                authors=authors,
                abstract=abstract,
                publication_year=year,
                venue=venue,
                is_open_access=pmc_id is not None,
                pdf_url=pdf_url,
                citation_count=None,
                reference_count=None,
                source_api="pubmed",
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse PubMed article: {e}")
            return None


# Convenience function
async def search_pubmed(
    query: str,
    limit: int = 25,
    **kwargs,
) -> PaperSearchResponse:
    """
    Search PubMed for papers (convenience function).
    
    Args:
        query: Search query.
        limit: Max results.
        **kwargs: Additional search parameters.
    
    Returns:
        PaperSearchResponse with results.
    """
    async with PubMedClient() as client:
        return await client.search(query, limit=limit, **kwargs)
