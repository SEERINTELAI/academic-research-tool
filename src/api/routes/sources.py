"""
Sources (Academic Papers) API routes.

Search, add, and manage academic paper sources for a project.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.deps import CurrentUser, DatabaseDep
from src.models.source import (
    Author,
    IngestionStatus,
    PaperSearchRequest,
    PaperSearchResponse,
    SourceCreate,
    SourceListItem,
    SourceResponse,
)
from src.services.semantic_scholar import (
    SemanticScholarClient,
    SemanticScholarError,
)
from src.services.multi_source_search import (
    MultiSourceSearchService,
    MultiSourceSearchResult,
    SearchSource,
)
from src.services.ingestion import IngestionService, IngestionError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/search",
    response_model=PaperSearchResponse,
    summary="Search for papers",
    description="Search academic databases for papers matching a query.",
)
async def search_papers(
    project_id: UUID,
    request: PaperSearchRequest,
    user: CurrentUser,
) -> PaperSearchResponse:
    """
    Search for academic papers.
    
    Uses Semantic Scholar API. Results can be added to the project.
    """
    try:
        async with SemanticScholarClient() as client:
            results = await client.search(
                query=request.query,
                limit=request.limit,
                year_from=request.year_from,
                year_to=request.year_to,
                open_access_only=request.open_access_only,
                fields_of_study=request.fields_of_study or None,
            )
        
        logger.info(f"Search '{request.query}' returned {len(results.results)} results")
        return results
        
    except SemanticScholarError as e:
        if e.status_code == 429:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Search API error: {e.message}",
        )


@router.post(
    "/search/multi",
    response_model=MultiSourceSearchResult,
    summary="Search multiple sources",
    description="Search multiple academic databases in parallel (OpenAlex, arXiv, PubMed, CrossRef, CORE).",
)
async def search_papers_multi(
    project_id: UUID,
    query: str = Query(..., min_length=1, max_length=1000, description="Search query"),
    limit_per_source: int = Query(25, ge=1, le=100, description="Max results per source"),
    sources: Optional[list[SearchSource]] = Query(
        None,
        description="Sources to search (default: openalex, arxiv, crossref)",
    ),
    year_from: Optional[int] = Query(None, description="Minimum publication year"),
    year_to: Optional[int] = Query(None, description="Maximum publication year"),
    deduplicate: bool = Query(True, description="Remove duplicates by DOI"),
    user: CurrentUser = None,
) -> MultiSourceSearchResult:
    """
    Search multiple academic paper databases in parallel.
    
    Available sources:
    - **openalex**: Free, comprehensive, no rate limits (default)
    - **arxiv**: CS, physics, math preprints
    - **pubmed**: Biomedical and life sciences
    - **crossref**: DOI registry, extensive metadata
    - **core**: Open access papers (may require API key for full access)
    - **semantic_scholar**: Comprehensive but strict rate limits
    
    Results are deduplicated by DOI and sorted by completeness of metadata.
    """
    try:
        service = MultiSourceSearchService()
        results = await service.search(
            query=query,
            sources=sources,
            limit_per_source=limit_per_source,
            year_from=year_from,
            year_to=year_to,
            deduplicate=deduplicate,
        )
        
        logger.info(
            f"Multi-source search '{query}' returned {results.total_results} results "
            f"from {len(results.source_counts)} sources"
        )
        
        if results.errors:
            logger.warning(f"Search errors: {results.errors}")
        
        return results
        
    except Exception as e:
        logger.exception(f"Multi-source search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Search error: {str(e)}",
        )


@router.post(
    "",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add paper to project",
    description="Add an academic paper to the project's sources.",
)
async def add_source(
    project_id: UUID,
    source: SourceCreate,
    user: CurrentUser,
    db: DatabaseDep,
) -> SourceResponse:
    """
    Add a paper to the project.
    
    The paper will be queued for ingestion into the RAG system.
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
    
    # Check if source already exists (by DOI or paper_id)
    if source.doi:
        existing = db.table("source")\
            .select("id")\
            .eq("project_id", str(project_id))\
            .eq("doi", source.doi)\
            .maybe_single()\
            .execute()
        
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Paper with DOI {source.doi} already exists in project",
            )
    
    try:
        # Convert authors to JSON-serializable format
        authors_json = [a.model_dump() for a in source.authors]
        
        # Insert source
        insert_data = {
            "project_id": str(project_id),
            "doi": source.doi,
            "arxiv_id": source.arxiv_id,
            "semantic_scholar_id": source.paper_id,
            "title": source.title,
            "authors": authors_json,
            "abstract": source.abstract,
            "publication_year": source.publication_year,
            "journal": source.venue,
            "pdf_url": source.pdf_url,
            "keywords": source.keywords,
            "ingestion_status": IngestionStatus.PENDING.value,
        }
        
        result = db.table("source").insert(insert_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add source",
            )
        
        created = result.data[0]
        logger.info(f"Added source {created['id']} to project {project_id}")
        
        # Parse authors back to model
        authors = [Author(**a) for a in (created.get("authors") or [])]
        
        return SourceResponse(
            id=created["id"],
            project_id=created["project_id"],
            doi=created.get("doi"),
            arxiv_id=created.get("arxiv_id"),
            semantic_scholar_id=created.get("semantic_scholar_id"),
            title=created["title"],
            authors=authors,
            abstract=created.get("abstract"),
            publication_year=created.get("publication_year"),
            journal=created.get("journal"),
            pdf_url=created.get("pdf_url"),
            ingestion_status=created["ingestion_status"],
            hyperion_doc_name=created.get("hyperion_doc_name"),
            chunk_count=created.get("chunk_count", 0),
            error_message=created.get("error_message"),
            created_at=created["created_at"],
            updated_at=created["updated_at"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error adding source: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.get(
    "",
    response_model=list[SourceListItem],
    summary="List project sources",
    description="List all academic paper sources in a project.",
)
async def list_sources(
    project_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
    status_filter: Optional[IngestionStatus] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[SourceListItem]:
    """List sources in a project."""
    try:
        query = db.table("source")\
            .select("id, title, authors, publication_year, ingestion_status, chunk_count, created_at")\
            .eq("project_id", str(project_id))
        
        if status_filter:
            query = query.eq("ingestion_status", status_filter.value)
        
        query = query.order("created_at", desc=True)\
            .range(offset, offset + limit - 1)
        
        result = query.execute()
        
        sources = []
        for row in result.data:
            authors = [Author(**a) for a in (row.get("authors") or [])]
            sources.append(SourceListItem(
                id=row["id"],
                title=row["title"],
                authors=authors,
                publication_year=row.get("publication_year"),
                ingestion_status=row["ingestion_status"],
                chunk_count=row.get("chunk_count", 0),
                created_at=row["created_at"],
            ))
        
        return sources
        
    except Exception as e:
        logger.exception(f"Error listing sources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.get(
    "/{source_id}",
    response_model=SourceResponse,
    summary="Get source details",
    description="Get details of a specific source.",
)
async def get_source(
    project_id: UUID,
    source_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
) -> SourceResponse:
    """Get source details."""
    try:
        result = db.table("source")\
            .select("*")\
            .eq("id", str(source_id))\
            .eq("project_id", str(project_id))\
            .maybe_single()\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found",
            )
        
        row = result.data
        authors = [Author(**a) for a in (row.get("authors") or [])]
        
        return SourceResponse(
            id=row["id"],
            project_id=row["project_id"],
            doi=row.get("doi"),
            arxiv_id=row.get("arxiv_id"),
            semantic_scholar_id=row.get("semantic_scholar_id"),
            title=row["title"],
            authors=authors,
            abstract=row.get("abstract"),
            publication_year=row.get("publication_year"),
            journal=row.get("journal"),
            pdf_url=row.get("pdf_url"),
            ingestion_status=row["ingestion_status"],
            hyperion_doc_name=row.get("hyperion_doc_name"),
            chunk_count=row.get("chunk_count", 0),
            error_message=row.get("error_message"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting source: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove source",
    description="Remove a source from the project (also deletes from LightRAG).",
)
async def delete_source(
    project_id: UUID,
    source_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
) -> None:
    """Remove a source from the project."""
    try:
        # First try to delete from LightRAG
        service = IngestionService()
        await service.delete_source_from_hyperion(source_id)
        
        # Then delete from database
        result = db.table("source")\
            .delete()\
            .eq("id", str(source_id))\
            .eq("project_id", str(project_id))\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found",
            )
        
        logger.info(f"Deleted source {source_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting source: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.post(
    "/{source_id}/ingest",
    summary="Ingest source to LightRAG",
    description="Download PDF and upload to LightRAG for automatic chunking and indexing.",
)
async def ingest_source(
    project_id: UUID,
    source_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
    force: bool = Query(False, description="Force re-ingestion even if already processed"),
) -> dict:
    """
    Ingest a source into LightRAG.
    
    Simplified pipeline:
    1. Download PDF (from arXiv, Unpaywall, or direct URL)
    2. Upload to LightRAG (automatic chunking + knowledge graph)
    
    The source will be ready for RAG queries after LightRAG processing.
    """
    # Verify source exists and belongs to project
    result = db.table("source")\
        .select("id, pdf_url, arxiv_id, doi")\
        .eq("id", str(source_id))\
        .eq("project_id", str(project_id))\
        .maybe_single()\
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    
    source = result.data
    
    # Check if source has a downloadable PDF
    if not source.get("pdf_url") and not source.get("arxiv_id") and not source.get("doi"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source has no PDF URL, arXiv ID, or DOI for download",
        )
    
    try:
        service = IngestionService()
        ingestion_result = await service.ingest_source(source_id, force)
        
        logger.info(f"Ingested source {source_id}: {ingestion_result}")
        return ingestion_result
        
    except IngestionError as e:
        logger.error(f"Ingestion failed for {source_id} at stage {e.stage}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Ingestion failed ({e.stage}): {e.message}",
        )
    except Exception as e:
        logger.exception(f"Unexpected ingestion error for {source_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion error: {str(e)}",
        )


@router.get(
    "/pipeline/status",
    summary="Get LightRAG pipeline status",
    description="Check if LightRAG is currently processing documents.",
)
async def get_pipeline_status(
    project_id: UUID,
    user: CurrentUser,
) -> dict:
    """
    Get the current status of the LightRAG processing pipeline.
    
    Useful for checking if uploads are still being processed.
    """
    try:
        service = IngestionService()
        status = await service.check_pipeline_status()
        return status
        
    except Exception as e:
        logger.exception(f"Error checking pipeline status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}",
        )
