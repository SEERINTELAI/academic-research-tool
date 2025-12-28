"""
Knowledge Tree / Citation Discovery API routes.

Explore the citation graph to discover related papers.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.deps import CurrentUser, DatabaseDep
from src.models.source import PaperSearchResult, SourceCreate
from src.services.discovery import DiscoveryService, RelationType
from src.services.semantic_scholar import SemanticScholarError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{source_id}/references",
    summary="Get papers this source cites",
    description="Discover papers in this source's bibliography (backward references).",
)
async def get_source_references(
    project_id: UUID,
    source_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    """
    Get papers that this source references (cites).
    
    These are the papers in the bibliography that the source
    was built upon. Useful for understanding the foundational work.
    """
    # Verify source exists
    result = db.table("source")\
        .select("id")\
        .eq("id", str(source_id))\
        .eq("project_id", str(project_id))\
        .maybe_single()\
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    
    try:
        service = DiscoveryService(project_id)
        discovery = await service.get_references(source_id, limit, offset)
        
        logger.info(
            f"Found {len(discovery.papers)} references for {source_id}"
        )
        return discovery.to_dict()
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except SemanticScholarError as e:
        if e.status_code == 429:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Semantic Scholar API error: {e.message}",
        )


@router.get(
    "/{source_id}/citations",
    summary="Get papers that cite this source",
    description="Discover papers that cite this source (forward citations).",
)
async def get_source_citations(
    project_id: UUID,
    source_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    """
    Get papers that cite this source.
    
    These are newer papers that reference this work.
    Useful for finding follow-up research and recent developments.
    """
    result = db.table("source")\
        .select("id")\
        .eq("id", str(source_id))\
        .eq("project_id", str(project_id))\
        .maybe_single()\
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    
    try:
        service = DiscoveryService(project_id)
        discovery = await service.get_citations(source_id, limit, offset)
        
        logger.info(
            f"Found {len(discovery.papers)} citations for {source_id}"
        )
        return discovery.to_dict()
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except SemanticScholarError as e:
        if e.status_code == 429:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Semantic Scholar API error: {e.message}",
        )


@router.get(
    "/{source_id}/related",
    summary="Get semantically related papers",
    description="Discover papers similar to this source based on content.",
)
async def get_related_papers(
    project_id: UUID,
    source_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
    limit: int = Query(10, ge=1, le=50),
) -> dict:
    """
    Get semantically related papers.
    
    Uses Semantic Scholar's recommendation engine to find
    papers with similar content and topics.
    """
    result = db.table("source")\
        .select("id")\
        .eq("id", str(source_id))\
        .eq("project_id", str(project_id))\
        .maybe_single()\
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    
    try:
        service = DiscoveryService(project_id)
        discovery = await service.get_related(source_id, limit)
        
        logger.info(
            f"Found {len(discovery.papers)} related papers for {source_id}"
        )
        return discovery.to_dict()
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except SemanticScholarError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Semantic Scholar API error: {e.message}",
        )


@router.get(
    "/{source_id}/discover",
    summary="Discover all related papers",
    description="Get references, citations, and related papers in one call.",
)
async def discover_all(
    project_id: UUID,
    source_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
    limit_per_type: int = Query(5, ge=1, le=20),
) -> dict:
    """
    Discover all types of related papers for a source.
    
    Returns:
    - References: Papers this source cites
    - Citations: Papers that cite this source
    - Related: Semantically similar papers
    """
    result = db.table("source")\
        .select("id")\
        .eq("id", str(source_id))\
        .eq("project_id", str(project_id))\
        .maybe_single()\
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    
    try:
        service = DiscoveryService(project_id)
        discovery = await service.discover_all(source_id, limit_per_type)
        
        return discovery
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/tree",
    summary="Explore project knowledge tree",
    description="Discover related papers for all sources in the project.",
)
async def explore_knowledge_tree(
    project_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
    limit_per_source: int = Query(3, ge=1, le=10),
) -> dict:
    """
    Explore the citation graph for the entire project.
    
    For each source in the project, discovers:
    - Papers it references
    - Papers that cite it
    - Semantically related papers
    
    Results are deduplicated across sources.
    """
    # Verify project exists
    project_result = db.table("project")\
        .select("id")\
        .eq("id", str(project_id))\
        .maybe_single()\
        .execute()
    
    if not project_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    try:
        service = DiscoveryService(project_id)
        tree = await service.explore_project_graph(
            depth=1,
            limit_per_source=limit_per_source,
        )
        
        logger.info(
            f"Explored knowledge tree for {project_id}: "
            f"{tree.get('sources_explored', 0)} sources"
        )
        return tree
        
    except Exception as e:
        logger.exception(f"Knowledge tree exploration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Exploration error: {str(e)}",
        )

