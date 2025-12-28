"""
Research Query Service.

Handles RAG queries against ingested academic papers.
Uses Hyperion for retrieval and formats responses with citations.
"""

import logging
import time
from typing import Optional
from uuid import UUID

from src.config import get_settings
from src.models.research import (
    CitationStyle,
    QueryMode,
    QueryRequest,
    QueryResponse,
    SourceReference,
)
from src.services.database import get_supabase_client
from src.services.hyperion_client import HyperionClient, HyperionError

logger = logging.getLogger(__name__)


class QueryError(Exception):
    """Query service error."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class QueryService:
    """
    Service for querying ingested academic papers.
    
    Workflow:
    1. Query Hyperion RAG
    2. Parse retrieved chunks
    3. Look up source metadata
    4. Format citations
    5. Return synthesized response
    
    Usage:
        service = QueryService(project_id)
        result = await service.query("What methods are used for X?")
    """
    
    def __init__(self, project_id: UUID):
        """
        Initialize query service.
        
        Args:
            project_id: Project to query within.
        """
        self.project_id = project_id
        self.db = get_supabase_client()
    
    async def query(self, request: QueryRequest) -> QueryResponse:
        """
        Execute a RAG query.
        
        Args:
            request: Query request with options.
        
        Returns:
            QueryResponse with answer and citations.
        """
        start_time = time.time()
        
        try:
            # Build query for Hyperion
            hyperion_query = self._build_hyperion_query(request)
            
            # Query Hyperion
            async with HyperionClient() as hyperion:
                rag_result = await hyperion.query(hyperion_query)
            
            # Parse sources from response
            sources = await self._parse_sources(rag_result.sources)
            
            # Format citations
            formatted_sources = self._format_citations(sources, request.citation_style)
            
            # Build final response
            answer = rag_result.response
            
            # Add inline citations if not already present
            if request.include_quotes and formatted_sources:
                answer = self._add_inline_citations(answer, formatted_sources)
            
            # Build reference list
            references = None
            if formatted_sources:
                references = self._build_reference_list(formatted_sources, request.citation_style)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return QueryResponse(
                query=request.query,
                answer=answer,
                sources=formatted_sources,
                total_chunks_searched=len(rag_result.sources),
                processing_time_ms=processing_time,
                formatted_references=references,
            )
            
        except HyperionError as e:
            logger.error(f"Hyperion query failed: {e.message}")
            raise QueryError(f"RAG query failed: {e.message}")
        except Exception as e:
            logger.exception(f"Query failed: {e}")
            raise QueryError(f"Query error: {str(e)}")
    
    def _build_hyperion_query(self, request: QueryRequest) -> str:
        """Build the query string for Hyperion."""
        parts = [request.query]
        
        # Add context instructions
        if request.section_types:
            parts.append(f"Focus on sections: {', '.join(request.section_types)}")
        
        if request.year_from or request.year_to:
            year_range = f"from {request.year_from or 'any'} to {request.year_to or 'present'}"
            parts.append(f"Consider papers {year_range}")
        
        # Add citation instruction
        parts.append("Include specific citations with author names and years for all claims.")
        
        return " ".join(parts)
    
    async def _parse_sources(
        self,
        raw_sources: list[dict],
    ) -> list[SourceReference]:
        """Parse and enrich source references from Hyperion response."""
        sources = []
        
        for raw in raw_sources:
            doc_name = raw.get("documentName", "")
            
            # Parse doc_name format: source_id[:8]_cXXX_section_type
            parts = doc_name.split("_")
            if len(parts) >= 3:
                source_id_prefix = parts[0]
                chunk_index = parts[1].replace("c", "")
                section_type = "_".join(parts[2:])
            else:
                source_id_prefix = doc_name
                chunk_index = "0"
                section_type = "unknown"
            
            # Look up full source info
            source_info = await self._lookup_source(source_id_prefix)
            
            if source_info:
                source = SourceReference(
                    source_id=source_info["id"],
                    title=source_info.get("title", "Unknown"),
                    authors=self._extract_author_names(source_info.get("authors", [])),
                    publication_year=source_info.get("publication_year"),
                    doi=source_info.get("doi"),
                    section_title=section_type.replace("_", " ").title(),
                    retrieved_text=raw.get("text", ""),
                )
                sources.append(source)
        
        return sources
    
    async def _lookup_source(self, source_id_prefix: str) -> Optional[dict]:
        """Look up source by ID prefix."""
        try:
            # Query for sources where ID starts with prefix
            result = self.db.table("source")\
                .select("id, title, authors, publication_year, doi")\
                .eq("project_id", str(self.project_id))\
                .execute()
            
            # Find matching source
            for source in result.data:
                if str(source["id"]).startswith(source_id_prefix):
                    return source
            
            return None
        except Exception as e:
            logger.warning(f"Source lookup failed: {e}")
            return None
    
    def _extract_author_names(self, authors: list) -> list[str]:
        """Extract author names from various formats."""
        names = []
        for author in authors:
            if isinstance(author, dict):
                name = author.get("name") or f"{author.get('first_name', '')} {author.get('last_name', '')}".strip()
                if name:
                    names.append(name)
            elif isinstance(author, str):
                names.append(author)
        return names
    
    def _format_citations(
        self,
        sources: list[SourceReference],
        style: CitationStyle,
    ) -> list[SourceReference]:
        """Format citations for each source."""
        for source in sources:
            source.in_text_citation = self._format_in_text_citation(source, style)
            source.full_citation = self._format_full_citation(source, style)
        return sources
    
    def _format_in_text_citation(
        self,
        source: SourceReference,
        style: CitationStyle,
    ) -> str:
        """Format in-text citation."""
        authors = source.authors
        year = source.publication_year or "n.d."
        
        if not authors:
            return f"({year})"
        
        first_author = authors[0].split()[-1]  # Last name
        
        if style == CitationStyle.APA:
            if len(authors) == 1:
                return f"({first_author}, {year})"
            elif len(authors) == 2:
                second_author = authors[1].split()[-1]
                return f"({first_author} & {second_author}, {year})"
            else:
                return f"({first_author} et al., {year})"
        
        elif style == CitationStyle.MLA:
            if len(authors) == 1:
                return f"({first_author})"
            elif len(authors) == 2:
                second_author = authors[1].split()[-1]
                return f"({first_author} and {second_author})"
            else:
                return f"({first_author} et al.)"
        
        elif style == CitationStyle.IEEE:
            # IEEE uses numbered references
            return "[REF]"  # Would be replaced with actual number
        
        else:
            return f"({first_author}, {year})"
    
    def _format_full_citation(
        self,
        source: SourceReference,
        style: CitationStyle,
    ) -> str:
        """Format full reference entry."""
        authors = source.authors
        year = source.publication_year or "n.d."
        title = source.title
        doi = source.doi
        
        if style == CitationStyle.APA:
            # Author, A. A., & Author, B. B. (Year). Title. DOI
            if authors:
                author_str = ", ".join(authors[:3])
                if len(authors) > 3:
                    author_str += " et al."
            else:
                author_str = "Unknown"
            
            citation = f"{author_str} ({year}). {title}."
            if doi:
                citation += f" https://doi.org/{doi}"
            return citation
        
        elif style == CitationStyle.MLA:
            # Author(s). "Title." Year.
            if authors:
                author_str = ", ".join(authors[:2])
                if len(authors) > 2:
                    author_str += ", et al"
            else:
                author_str = "Unknown"
            return f'{author_str}. "{title}." {year}.'
        
        else:
            # Default format
            author_str = ", ".join(authors[:3]) if authors else "Unknown"
            return f"{author_str}. {title}. {year}."
    
    def _add_inline_citations(
        self,
        answer: str,
        sources: list[SourceReference],
    ) -> str:
        """Add inline citations to answer if not already present."""
        # Simple heuristic: if answer doesn't have citations, add them
        if "(" not in answer or ")" not in answer:
            # Add general citation at end
            citations = [s.in_text_citation for s in sources if s.in_text_citation]
            if citations:
                unique_citations = list(dict.fromkeys(citations))  # Dedupe
                answer += "\n\n" + " ".join(unique_citations)
        return answer
    
    def _build_reference_list(
        self,
        sources: list[SourceReference],
        style: CitationStyle,
    ) -> str:
        """Build formatted reference list."""
        # Dedupe by source_id
        seen = set()
        unique_sources = []
        for source in sources:
            if source.source_id not in seen:
                seen.add(source.source_id)
                unique_sources.append(source)
        
        # Sort by author
        unique_sources.sort(key=lambda s: s.authors[0] if s.authors else "ZZZ")
        
        lines = ["References", ""]
        for source in unique_sources:
            if source.full_citation:
                lines.append(source.full_citation)
        
        return "\n".join(lines)
    
    async def save_synthesis(
        self,
        query: str,
        answer: str,
        sources: list[SourceReference],
        outline_section_id: Optional[UUID] = None,
    ) -> UUID:
        """Save a synthesis to the database."""
        # Convert sources to JSON-serializable format
        sources_json = [s.model_dump(mode="json") for s in sources]
        
        result = self.db.table("synthesis").insert({
            "project_id": str(self.project_id),
            "query": query,
            "answer": answer,
            "sources": sources_json,
            "outline_section_id": str(outline_section_id) if outline_section_id else None,
        }).execute()
        
        if result.data:
            return UUID(result.data[0]["id"])
        raise QueryError("Failed to save synthesis")


# Convenience function
async def query_project(
    project_id: UUID,
    query: str,
    **kwargs,
) -> QueryResponse:
    """Query a project's sources (convenience function)."""
    request = QueryRequest(query=query, **kwargs)
    service = QueryService(project_id)
    return await service.query(request)

