"""
Multi-Source Academic Paper Search.

Aggregates results from multiple academic paper APIs:
- OpenAlex (default, no rate limits)
- arXiv (CS, physics, math - 1 req/3s)
- PubMed (biomedical - 3 req/s without key)
- CrossRef (DOI registry - generous limits)
- CORE (open access - requires API key)
- Semantic Scholar (comprehensive - strict rate limits)

Searches run in parallel with deduplication by DOI.
"""

import asyncio
import logging
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from src.models.source import PaperSearchResult, PaperSearchResponse
from src.services.openalex import OpenAlexClient
from src.services.arxiv import ArxivClient
from src.services.pubmed import PubMedClient
from src.services.crossref import CrossRefClient
from src.services.core import CoreClient
from src.services.semantic_scholar import SemanticScholarClient

logger = logging.getLogger(__name__)


class SearchSource(str, Enum):
    """Available academic paper sources."""
    OPENALEX = "openalex"
    ARXIV = "arxiv"
    PUBMED = "pubmed"
    CROSSREF = "crossref"
    CORE = "core"
    SEMANTIC_SCHOLAR = "semantic_scholar"


class MultiSourceSearchRequest(BaseModel):
    """Request to search multiple sources."""
    
    query: str = Field(..., min_length=1, max_length=1000)
    limit_per_source: int = Field(default=25, ge=1, le=100)
    sources: list[SearchSource] = Field(
        default_factory=lambda: [
            SearchSource.OPENALEX,
            SearchSource.ARXIV,
            SearchSource.CROSSREF,
        ]
    )
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    deduplicate: bool = True  # Remove duplicates by DOI


class MultiSourceSearchResult(BaseModel):
    """Results from multi-source search."""
    
    query: str
    total_results: int
    results: list[PaperSearchResult]
    source_counts: dict[str, int] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)


class MultiSourceSearchService:
    """
    Service for searching multiple academic paper APIs in parallel.
    
    Usage:
        async with MultiSourceSearchService() as service:
            results = await service.search(
                query="machine learning",
                sources=[SearchSource.OPENALEX, SearchSource.ARXIV],
                limit_per_source=50,
            )
    """
    
    def __init__(
        self,
        core_api_key: Optional[str] = None,
        semantic_scholar_api_key: Optional[str] = None,
        email: Optional[str] = None,
    ):
        """
        Initialize multi-source search service.
        
        Args:
            core_api_key: Optional CORE API key for higher limits.
            semantic_scholar_api_key: Optional Semantic Scholar key.
            email: Email for polite pool access.
        """
        self.core_api_key = core_api_key
        self.semantic_scholar_api_key = semantic_scholar_api_key
        self.email = email or "academic-research-tool@example.com"
    
    async def search(
        self,
        query: str,
        sources: Optional[list[SearchSource]] = None,
        limit_per_source: int = 25,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        deduplicate: bool = True,
    ) -> MultiSourceSearchResult:
        """
        Search multiple sources in parallel.
        
        Args:
            query: Search query.
            sources: Which sources to search (default: OpenAlex, arXiv, CrossRef).
            limit_per_source: Max results per source.
            year_from: Minimum publication year.
            year_to: Maximum publication year.
            deduplicate: Remove duplicates by DOI.
        
        Returns:
            Aggregated search results.
        """
        if sources is None:
            sources = [
                SearchSource.OPENALEX,
                SearchSource.ARXIV,
                SearchSource.CROSSREF,
            ]
        
        # Create search tasks for each source
        tasks = []
        source_names = []
        
        for source in sources:
            task = self._search_source(
                source=source,
                query=query,
                limit=limit_per_source,
                year_from=year_from,
                year_to=year_to,
            )
            tasks.append(task)
            source_names.append(source.value)
        
        # Run all searches in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        all_papers: list[PaperSearchResult] = []
        source_counts: dict[str, int] = {}
        errors: dict[str, str] = {}
        
        for source_name, result in zip(source_names, results):
            if isinstance(result, Exception):
                logger.warning(f"Search failed for {source_name}: {result}")
                errors[source_name] = str(result)
                source_counts[source_name] = 0
            elif isinstance(result, PaperSearchResponse):
                source_counts[source_name] = len(result.results)
                all_papers.extend(result.results)
            else:
                logger.warning(f"Unexpected result type from {source_name}: {type(result)}")
                source_counts[source_name] = 0
        
        # Deduplicate by DOI
        if deduplicate:
            all_papers = self._deduplicate_papers(all_papers)
        
        return MultiSourceSearchResult(
            query=query,
            total_results=len(all_papers),
            results=all_papers,
            source_counts=source_counts,
            errors=errors,
        )
    
    async def _search_source(
        self,
        source: SearchSource,
        query: str,
        limit: int,
        year_from: Optional[int],
        year_to: Optional[int],
    ) -> PaperSearchResponse:
        """Search a single source."""
        
        if source == SearchSource.OPENALEX:
            async with OpenAlexClient(email=self.email) as client:
                result = await client.search(query, limit=limit)
                # Convert to standard format
                return PaperSearchResponse(
                    query=query,
                    total_results=result.total,
                    results=[
                        PaperSearchResult(
                            paper_id=p.paper_id,
                            doi=p.doi,
                            arxiv_id=p.external_ids.get("arxiv"),
                            title=p.title,
                            authors=[
                                {"name": a.name, "orcid": a.orcid}  # type: ignore
                                for a in p.authors
                            ],
                            abstract=p.abstract,
                            publication_year=p.year,
                            venue=p.venue,
                            is_open_access=p.open_access_url is not None,
                            pdf_url=p.pdf_url or p.open_access_url,
                            citation_count=p.citation_count,
                            source_api="openalex",
                        )
                        for p in result.results
                    ],
                )
        
        elif source == SearchSource.ARXIV:
            async with ArxivClient() as client:
                return await client.search(query, limit=limit)
        
        elif source == SearchSource.PUBMED:
            async with PubMedClient(email=self.email) as client:
                return await client.search(query, limit=limit)
        
        elif source == SearchSource.CROSSREF:
            async with CrossRefClient(email=self.email) as client:
                # CrossRef supports date filtering
                from_date = f"{year_from}-01-01" if year_from else None
                until_date = f"{year_to}-12-31" if year_to else None
                return await client.search(
                    query,
                    limit=limit,
                    from_pub_date=from_date,
                    until_pub_date=until_date,
                )
        
        elif source == SearchSource.CORE:
            async with CoreClient(api_key=self.core_api_key) as client:
                return await client.search(
                    query,
                    limit=limit,
                    year_from=year_from,
                    year_to=year_to,
                )
        
        elif source == SearchSource.SEMANTIC_SCHOLAR:
            async with SemanticScholarClient(api_key=self.semantic_scholar_api_key) as client:
                return await client.search(
                    query,
                    limit=limit,
                    year_from=year_from,
                    year_to=year_to,
                )
        
        else:
            raise ValueError(f"Unknown source: {source}")
    
    def _deduplicate_papers(
        self,
        papers: list[PaperSearchResult],
    ) -> list[PaperSearchResult]:
        """
        Remove duplicate papers based on DOI.
        
        Papers without DOI are kept (no way to detect duplicates).
        When duplicates found, prefer the one with more metadata.
        """
        seen_dois: dict[str, PaperSearchResult] = {}
        unique_papers: list[PaperSearchResult] = []
        
        for paper in papers:
            if paper.doi:
                doi_lower = paper.doi.lower()
                if doi_lower in seen_dois:
                    # Compare and keep the one with more metadata
                    existing = seen_dois[doi_lower]
                    if self._paper_quality_score(paper) > self._paper_quality_score(existing):
                        seen_dois[doi_lower] = paper
                        # Replace in list
                        for i, p in enumerate(unique_papers):
                            if p.doi and p.doi.lower() == doi_lower:
                                unique_papers[i] = paper
                                break
                else:
                    seen_dois[doi_lower] = paper
                    unique_papers.append(paper)
            else:
                # No DOI - keep it (might be duplicate but can't tell)
                unique_papers.append(paper)
        
        return unique_papers
    
    def _paper_quality_score(self, paper: PaperSearchResult) -> int:
        """Score a paper by completeness of metadata."""
        score = 0
        if paper.abstract:
            score += 3
        if paper.authors:
            score += 2
        if paper.pdf_url:
            score += 2
        if paper.citation_count is not None:
            score += 1
        if paper.publication_year:
            score += 1
        if paper.venue:
            score += 1
        return score


# Convenience function
async def search_all_sources(
    query: str,
    sources: Optional[list[SearchSource]] = None,
    limit_per_source: int = 25,
    **kwargs,
) -> MultiSourceSearchResult:
    """
    Search multiple academic paper sources in parallel.
    
    Args:
        query: Search query.
        sources: Which sources to search.
        limit_per_source: Max results per source.
        **kwargs: Additional parameters.
    
    Returns:
        Aggregated results from all sources.
    """
    service = MultiSourceSearchService()
    return await service.search(
        query=query,
        sources=sources,
        limit_per_source=limit_per_source,
        **kwargs,
    )
