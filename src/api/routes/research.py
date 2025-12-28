"""
Research API routes.

RAG queries, synthesis, and comparison endpoints.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.deps import CurrentUser, DatabaseDep
from src.models.research import (
    QueryRequest,
    QueryResponse,
    SynthesisCreate,
    SynthesisResponse,
    SynthesisListItem,
    SourceReference,
)
from src.services.query_service import QueryService, QueryError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Query project sources",
    description="RAG query against ingested academic papers with citations.",
)
async def query_sources(
    project_id: UUID,
    request: QueryRequest,
    user: CurrentUser,
    db: DatabaseDep,
) -> QueryResponse:
    """
    Query ingested sources using RAG.
    
    The query is sent to Hyperion which retrieves relevant chunks
    from ingested papers. Results are synthesized with inline citations.
    
    Response includes:
    - Synthesized answer with inline citations
    - List of source references with page numbers
    - Formatted reference list
    """
    # Verify project exists and user has access
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
        service = QueryService(project_id)
        result = await service.query(request)
        
        logger.info(
            f"Query for project {project_id}: "
            f"'{request.query[:50]}...' returned {len(result.sources)} sources"
        )
        return result
        
    except QueryError as e:
        logger.error(f"Query failed for {project_id}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Query failed: {e.message}",
        )
    except Exception as e:
        logger.exception(f"Unexpected query error for {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query error: {str(e)}",
        )


@router.post(
    "/synthesis",
    response_model=SynthesisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save synthesis",
    description="Save a query result for later use in reports.",
)
async def save_synthesis(
    project_id: UUID,
    synthesis: SynthesisCreate,
    user: CurrentUser,
    db: DatabaseDep,
) -> SynthesisResponse:
    """
    Save a synthesis for use in reports.
    
    Syntheses can be linked to outline sections and pinned
    for easy access.
    """
    # Verify project
    if str(synthesis.project_id) != str(project_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project ID mismatch",
        )
    
    try:
        # Convert sources to JSON
        sources_json = [s.model_dump(mode="json") for s in synthesis.sources]
        
        result = db.table("synthesis").insert({
            "project_id": str(project_id),
            "query": synthesis.query,
            "answer": synthesis.answer,
            "sources": sources_json,
            "outline_section_id": str(synthesis.outline_section_id) if synthesis.outline_section_id else None,
            "user_notes": synthesis.user_notes,
            "is_pinned": synthesis.is_pinned,
        }).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save synthesis",
            )
        
        row = result.data[0]
        sources = [SourceReference(**s) for s in (row.get("sources") or [])]
        
        return SynthesisResponse(
            id=row["id"],
            project_id=row["project_id"],
            query=row["query"],
            answer=row["answer"],
            sources=sources,
            outline_section_id=row.get("outline_section_id"),
            user_notes=row.get("user_notes"),
            is_pinned=row.get("is_pinned", False),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error saving synthesis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.get(
    "/synthesis",
    response_model=list[SynthesisListItem],
    summary="List syntheses",
    description="List saved syntheses for a project.",
)
async def list_syntheses(
    project_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
    pinned_only: bool = Query(False),
    section_id: Optional[UUID] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[SynthesisListItem]:
    """List syntheses with optional filtering."""
    try:
        query = db.table("synthesis")\
            .select("id, query, answer, sources, is_pinned, created_at")\
            .eq("project_id", str(project_id))
        
        if pinned_only:
            query = query.eq("is_pinned", True)
        
        if section_id:
            query = query.eq("outline_section_id", str(section_id))
        
        query = query.order("created_at", desc=True)\
            .range(offset, offset + limit - 1)
        
        result = query.execute()
        
        items = []
        for row in result.data:
            sources = row.get("sources") or []
            answer = row.get("answer", "")
            items.append(SynthesisListItem(
                id=row["id"],
                query=row["query"],
                answer_preview=answer[:200] if len(answer) > 200 else answer,
                source_count=len(sources),
                is_pinned=row.get("is_pinned", False),
                created_at=row["created_at"],
            ))
        
        return items
        
    except Exception as e:
        logger.exception(f"Error listing syntheses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.get(
    "/synthesis/{synthesis_id}",
    response_model=SynthesisResponse,
    summary="Get synthesis",
    description="Get a specific synthesis with full details.",
)
async def get_synthesis(
    project_id: UUID,
    synthesis_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
) -> SynthesisResponse:
    """Get synthesis details."""
    try:
        result = db.table("synthesis")\
            .select("*")\
            .eq("id", str(synthesis_id))\
            .eq("project_id", str(project_id))\
            .maybe_single()\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Synthesis not found",
            )
        
        row = result.data
        sources = [SourceReference(**s) for s in (row.get("sources") or [])]
        
        return SynthesisResponse(
            id=row["id"],
            project_id=row["project_id"],
            query=row["query"],
            answer=row["answer"],
            sources=sources,
            outline_section_id=row.get("outline_section_id"),
            user_notes=row.get("user_notes"),
            is_pinned=row.get("is_pinned", False),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting synthesis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.delete(
    "/synthesis/{synthesis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete synthesis",
    description="Delete a saved synthesis.",
)
async def delete_synthesis(
    project_id: UUID,
    synthesis_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
) -> None:
    """Delete a synthesis."""
    try:
        result = db.table("synthesis")\
            .delete()\
            .eq("id", str(synthesis_id))\
            .eq("project_id", str(project_id))\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Synthesis not found",
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting synthesis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )

