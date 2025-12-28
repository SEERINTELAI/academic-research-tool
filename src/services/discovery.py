"""
Knowledge Tree / Citation Discovery Service.

Discovers related papers through citation graph exploration:
1. References - papers this paper cites (backward)
2. Citations - papers that cite this paper (forward)
3. Related - semantically similar papers

Uses Semantic Scholar's citation APIs.
"""

import logging
from enum import Enum
from typing import Optional
from uuid import UUID

from src.models.source import Author, PaperSearchResult
from src.services.database import get_supabase_client
from src.services.semantic_scholar import SemanticScholarClient, SemanticScholarError

logger = logging.getLogger(__name__)


class RelationType(str, Enum):
    """Type of relationship between papers."""
    
    REFERENCES = "references"  # Papers this paper cites
    CITED_BY = "cited_by"  # Papers citing this paper
    RELATED = "related"  # Semantically similar


class DiscoveryResult:
    """Result from citation discovery."""
    
    def __init__(
        self,
        source_id: UUID,
        source_title: str,
        relation_type: RelationType,
        papers: list[PaperSearchResult],
        total_available: int,
    ):
        self.source_id = source_id
        self.source_title = source_title
        self.relation_type = relation_type
        self.papers = papers
        self.total_available = total_available
    
    def to_dict(self) -> dict:
        return {
            "source_id": str(self.source_id),
            "source_title": self.source_title,
            "relation_type": self.relation_type.value,
            "papers": [p.model_dump() for p in self.papers],
            "total_available": self.total_available,
            "returned_count": len(self.papers),
        }


class DiscoveryService:
    """
    Service for discovering related papers via citation graph.
    
    The "Knowledge Tree" concept:
    - Start with papers in your project
    - Explore their references (what they cite)
    - Explore their citations (who cites them)
    - Find semantically related papers
    - Add promising ones to your project
    
    Usage:
        service = DiscoveryService(project_id)
        references = await service.get_references(source_id)
        citations = await service.get_citations(source_id)
    """
    
    def __init__(self, project_id: UUID):
        """
        Initialize discovery service.
        
        Args:
            project_id: Project ID for context.
        """
        self.project_id = project_id
        self.db = get_supabase_client()
    
    async def get_references(
        self,
        source_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> DiscoveryResult:
        """
        Get papers that this source references (cites).
        
        These are the papers in the bibliography.
        
        Args:
            source_id: Source to explore.
            limit: Max papers to return.
            offset: Pagination offset.
        
        Returns:
            DiscoveryResult with referenced papers.
        """
        source = self._get_source(source_id)
        if not source:
            raise ValueError(f"Source not found: {source_id}")
        
        paper_id = self._get_semantic_scholar_id(source)
        if not paper_id:
            raise ValueError("Source has no Semantic Scholar ID, DOI, or arXiv ID")
        
        async with SemanticScholarClient() as client:
            try:
                papers, total = await self._fetch_references(
                    client, paper_id, limit, offset
                )
                
                return DiscoveryResult(
                    source_id=source_id,
                    source_title=source.get("title", "Unknown"),
                    relation_type=RelationType.REFERENCES,
                    papers=papers,
                    total_available=total,
                )
            except SemanticScholarError as e:
                logger.error(f"Failed to get references: {e.message}")
                raise
    
    async def get_citations(
        self,
        source_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> DiscoveryResult:
        """
        Get papers that cite this source.
        
        These are newer papers that reference this one.
        
        Args:
            source_id: Source to explore.
            limit: Max papers to return.
            offset: Pagination offset.
        
        Returns:
            DiscoveryResult with citing papers.
        """
        source = self._get_source(source_id)
        if not source:
            raise ValueError(f"Source not found: {source_id}")
        
        paper_id = self._get_semantic_scholar_id(source)
        if not paper_id:
            raise ValueError("Source has no Semantic Scholar ID, DOI, or arXiv ID")
        
        async with SemanticScholarClient() as client:
            try:
                papers, total = await self._fetch_citations(
                    client, paper_id, limit, offset
                )
                
                return DiscoveryResult(
                    source_id=source_id,
                    source_title=source.get("title", "Unknown"),
                    relation_type=RelationType.CITED_BY,
                    papers=papers,
                    total_available=total,
                )
            except SemanticScholarError as e:
                logger.error(f"Failed to get citations: {e.message}")
                raise
    
    async def get_related(
        self,
        source_id: UUID,
        limit: int = 10,
    ) -> DiscoveryResult:
        """
        Get semantically related papers.
        
        Uses Semantic Scholar's recommendations API.
        
        Args:
            source_id: Source to find similar papers for.
            limit: Max papers to return.
        
        Returns:
            DiscoveryResult with related papers.
        """
        source = self._get_source(source_id)
        if not source:
            raise ValueError(f"Source not found: {source_id}")
        
        paper_id = self._get_semantic_scholar_id(source)
        if not paper_id:
            raise ValueError("Source has no Semantic Scholar ID, DOI, or arXiv ID")
        
        async with SemanticScholarClient() as client:
            try:
                papers = await self._fetch_recommendations(client, paper_id, limit)
                
                return DiscoveryResult(
                    source_id=source_id,
                    source_title=source.get("title", "Unknown"),
                    relation_type=RelationType.RELATED,
                    papers=papers,
                    total_available=len(papers),
                )
            except SemanticScholarError as e:
                logger.error(f"Failed to get recommendations: {e.message}")
                raise
    
    async def discover_all(
        self,
        source_id: UUID,
        limit_per_type: int = 5,
    ) -> dict:
        """
        Get all discovery types for a source.
        
        Returns references, citations, and related papers.
        
        Args:
            source_id: Source to explore.
            limit_per_type: Max papers per relation type.
        
        Returns:
            Dict with all discovery results.
        """
        results = {}
        
        try:
            refs = await self.get_references(source_id, limit=limit_per_type)
            results["references"] = refs.to_dict()
        except Exception as e:
            logger.warning(f"Failed to get references: {e}")
            results["references"] = {"error": str(e)}
        
        try:
            cites = await self.get_citations(source_id, limit=limit_per_type)
            results["citations"] = cites.to_dict()
        except Exception as e:
            logger.warning(f"Failed to get citations: {e}")
            results["citations"] = {"error": str(e)}
        
        try:
            related = await self.get_related(source_id, limit=limit_per_type)
            results["related"] = related.to_dict()
        except Exception as e:
            logger.warning(f"Failed to get related: {e}")
            results["related"] = {"error": str(e)}
        
        return results
    
    async def explore_project_graph(
        self,
        depth: int = 1,
        limit_per_source: int = 5,
    ) -> dict:
        """
        Explore citation graph for all sources in project.
        
        Builds a "knowledge tree" by discovering related papers
        for each source in the project.
        
        Args:
            depth: How many levels to explore (1 = immediate refs/cites).
            limit_per_source: Max discoveries per source per type.
        
        Returns:
            Dict mapping source_id to discovery results.
        """
        # Get all sources in project
        result = self.db.table("source")\
            .select("id, title, semantic_scholar_id, doi, arxiv_id")\
            .eq("project_id", str(self.project_id))\
            .execute()
        
        if not result.data:
            return {"sources": [], "discoveries": {}}
        
        discoveries = {}
        seen_papers = set()  # Track papers we've already seen
        
        for source in result.data:
            source_id = UUID(source["id"])
            
            # Skip sources without identifiers
            if not self._get_semantic_scholar_id(source):
                continue
            
            try:
                discovery = await self.discover_all(source_id, limit_per_type=limit_per_source)
                
                # Filter out papers already in project
                for relation_type in ["references", "citations", "related"]:
                    if relation_type in discovery and "papers" in discovery[relation_type]:
                        papers = discovery[relation_type]["papers"]
                        discovery[relation_type]["papers"] = [
                            p for p in papers
                            if p.get("paper_id") not in seen_papers
                        ]
                        # Track seen papers
                        for p in discovery[relation_type]["papers"]:
                            seen_papers.add(p.get("paper_id"))
                
                discoveries[str(source_id)] = discovery
                
            except Exception as e:
                logger.warning(f"Failed to discover for {source_id}: {e}")
                discoveries[str(source_id)] = {"error": str(e)}
        
        return {
            "project_id": str(self.project_id),
            "sources_explored": len(discoveries),
            "discoveries": discoveries,
        }
    
    def _get_source(self, source_id: UUID) -> Optional[dict]:
        """Get source from database."""
        result = self.db.table("source")\
            .select("*")\
            .eq("id", str(source_id))\
            .eq("project_id", str(self.project_id))\
            .maybe_single()\
            .execute()
        return result.data
    
    def _get_semantic_scholar_id(self, source: dict) -> Optional[str]:
        """Get the best identifier for Semantic Scholar lookup."""
        if source.get("semantic_scholar_id"):
            return source["semantic_scholar_id"]
        if source.get("doi"):
            return f"DOI:{source['doi']}"
        if source.get("arxiv_id"):
            return f"ARXIV:{source['arxiv_id']}"
        return None
    
    async def _fetch_references(
        self,
        client: SemanticScholarClient,
        paper_id: str,
        limit: int,
        offset: int,
    ) -> tuple[list[PaperSearchResult], int]:
        """Fetch references from Semantic Scholar."""
        # Use the references endpoint
        response = await client._client.get(
            f"/paper/{paper_id}/references",
            params={
                "fields": "paperId,externalIds,title,abstract,venue,year,authors,citationCount,isOpenAccess,openAccessPdf",
                "limit": limit,
                "offset": offset,
            },
        )
        
        if response.status_code != 200:
            raise SemanticScholarError(f"References API error: {response.text}", response.status_code)
        
        data = response.json()
        papers = []
        
        for item in data.get("data", []):
            cited_paper = item.get("citedPaper", {})
            if cited_paper and cited_paper.get("paperId"):
                papers.append(client._parse_paper(cited_paper))
        
        total = data.get("total", len(papers))
        return papers, total
    
    async def _fetch_citations(
        self,
        client: SemanticScholarClient,
        paper_id: str,
        limit: int,
        offset: int,
    ) -> tuple[list[PaperSearchResult], int]:
        """Fetch citations from Semantic Scholar."""
        response = await client._client.get(
            f"/paper/{paper_id}/citations",
            params={
                "fields": "paperId,externalIds,title,abstract,venue,year,authors,citationCount,isOpenAccess,openAccessPdf",
                "limit": limit,
                "offset": offset,
            },
        )
        
        if response.status_code != 200:
            raise SemanticScholarError(f"Citations API error: {response.text}", response.status_code)
        
        data = response.json()
        papers = []
        
        for item in data.get("data", []):
            citing_paper = item.get("citingPaper", {})
            if citing_paper and citing_paper.get("paperId"):
                papers.append(client._parse_paper(citing_paper))
        
        total = data.get("total", len(papers))
        return papers, total
    
    async def _fetch_recommendations(
        self,
        client: SemanticScholarClient,
        paper_id: str,
        limit: int,
    ) -> list[PaperSearchResult]:
        """Fetch recommendations from Semantic Scholar."""
        response = await client._client.get(
            f"/recommendations/v1/papers/forpaper/{paper_id}",
            params={
                "fields": "paperId,externalIds,title,abstract,venue,year,authors,citationCount,isOpenAccess,openAccessPdf",
                "limit": limit,
            },
        )
        
        if response.status_code != 200:
            # Recommendations API might not be available for all papers
            logger.warning(f"Recommendations not available: {response.status_code}")
            return []
        
        data = response.json()
        papers = []
        
        for paper in data.get("recommendedPapers", []):
            if paper.get("paperId"):
                papers.append(client._parse_paper(paper))
        
        return papers


# Convenience functions
async def discover_references(project_id: UUID, source_id: UUID, limit: int = 20) -> DiscoveryResult:
    """Get papers referenced by a source."""
    service = DiscoveryService(project_id)
    return await service.get_references(source_id, limit)


async def discover_citations(project_id: UUID, source_id: UUID, limit: int = 20) -> DiscoveryResult:
    """Get papers that cite a source."""
    service = DiscoveryService(project_id)
    return await service.get_citations(source_id, limit)


async def explore_knowledge_tree(project_id: UUID, depth: int = 1) -> dict:
    """Explore the citation graph for all project sources."""
    service = DiscoveryService(project_id)
    return await service.explore_project_graph(depth=depth)

