"""
Test harness API endpoints.

Provides programmatic access to simulate full user flows for testing.
These endpoints allow API-first testing of all UI interactions without a browser.

NOTE: These endpoints are for development/testing only and should be
disabled or protected in production.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.deps import DatabaseDep, CurrentUser
from src.config import get_settings
from src.models.project import ProjectCreate, ProjectStatus
from src.services.database import check_database_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/test", tags=["test-harness"])


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateProjectRequest(BaseModel):
    """Request to create a test project."""
    title: str = Field(default_factory=lambda: f"Test Project {uuid4().hex[:8]}")
    description: Optional[str] = "Created via test harness"


class CreateProjectResponse(BaseModel):
    """Response from creating a test project."""
    project_id: str
    title: str
    status: str


class SearchPapersRequest(BaseModel):
    """Request to search for papers."""
    query: str
    limit: int = Field(default=10, ge=1, le=50)


class SearchPapersResponse(BaseModel):
    """Response from searching papers."""
    query: str
    results_count: int
    paper_ids: list[str]
    execution_time_ms: float


class IngestPaperRequest(BaseModel):
    """Request to ingest a paper."""
    project_id: str
    paper_id: Optional[str] = None
    title: str
    pdf_url: Optional[str] = None


class IngestPaperResponse(BaseModel):
    """Response from ingesting a paper."""
    source_id: str
    status: str
    message: str


class GenerateOutlineRequest(BaseModel):
    """Request to generate an outline."""
    project_id: str
    topic: Optional[str] = None


class GenerateOutlineResponse(BaseModel):
    """Response from generating an outline."""
    project_id: str
    sections_created: int
    section_titles: list[str]


class FullResearchFlowRequest(BaseModel):
    """Request for complete research workflow."""
    topic: str
    num_papers: int = Field(default=5, ge=1, le=20)
    generate_outline: bool = True


class FullResearchFlowResponse(BaseModel):
    """Response from complete research workflow."""
    project_id: str
    project_title: str
    papers_found: int
    papers_ingested: int
    outline_sections: int
    execution_time_ms: float
    steps_completed: list[str]


class DiagnosticsResponse(BaseModel):
    """System diagnostics response."""
    timestamp: datetime
    backend_status: str
    database_connected: bool
    lightrag_available: bool
    recent_errors: list[dict]
    request_count: int
    active_projects: int
    environment: str


# =============================================================================
# Test Endpoints
# =============================================================================

@router.post(
    "/create-project",
    response_model=CreateProjectResponse,
    summary="Create a test project",
    description="Create a project for testing purposes. Returns project ID.",
)
async def create_test_project(
    request: CreateProjectRequest,
    user: CurrentUser,
    db: DatabaseDep,
) -> CreateProjectResponse:
    """Create a test project and return its ID."""
    try:
        result = db.table("project").insert({
            "title": request.title,
            "description": request.description,
            "status": ProjectStatus.DRAFT.value,
        }).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create test project",
            )
        
        project = result.data[0]
        logger.info(f"Test harness created project: {project['id']}")
        
        return CreateProjectResponse(
            project_id=project["id"],
            title=project["title"],
            status=project["status"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Test harness error creating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/search-papers",
    response_model=SearchPapersResponse,
    summary="Search for papers",
    description="Search academic databases for papers. Returns paper IDs.",
)
async def search_papers_test(
    request: SearchPapersRequest,
    user: CurrentUser,
) -> SearchPapersResponse:
    """Search for papers via Semantic Scholar."""
    import time
    start = time.time()
    
    try:
        # Import here to avoid circular imports
        from src.services.semantic_scholar import search_papers
        
        results = await search_papers(request.query, limit=request.limit)
        
        execution_time = (time.time() - start) * 1000
        
        return SearchPapersResponse(
            query=request.query,
            results_count=len(results),
            paper_ids=[p.get("paperId", "") for p in results],
            execution_time_ms=execution_time,
        )
        
    except ImportError:
        # Service not implemented yet
        return SearchPapersResponse(
            query=request.query,
            results_count=0,
            paper_ids=[],
            execution_time_ms=(time.time() - start) * 1000,
        )
    except Exception as e:
        logger.exception(f"Test harness error searching papers: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Paper search failed: {str(e)}",
        )


@router.post(
    "/ingest-paper",
    response_model=IngestPaperResponse,
    summary="Ingest a paper",
    description="Add and ingest a paper to a project's RAG index.",
)
async def ingest_paper_test(
    request: IngestPaperRequest,
    user: CurrentUser,
    db: DatabaseDep,
) -> IngestPaperResponse:
    """Ingest a paper to RAG."""
    try:
        # Create source record
        source_data = {
            "project_id": request.project_id,
            "paper_id": request.paper_id,
            "title": request.title,
            "pdf_url": request.pdf_url,
            "ingestion_status": "pending",
            "authors": [],
        }
        
        result = db.table("source").insert(source_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create source record",
            )
        
        source = result.data[0]
        
        # TODO: Trigger actual ingestion via LightRAG
        # For now, just mark as pending
        
        return IngestPaperResponse(
            source_id=source["id"],
            status="pending",
            message="Paper queued for ingestion",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Test harness error ingesting paper: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/generate-outline",
    response_model=GenerateOutlineResponse,
    summary="Generate an outline",
    description="Generate an outline for a project using AI.",
)
async def generate_outline_test(
    request: GenerateOutlineRequest,
    user: CurrentUser,
    db: DatabaseDep,
) -> GenerateOutlineResponse:
    """Generate outline sections for a project."""
    try:
        # Create basic outline sections
        sections = [
            {"title": "Introduction", "section_type": "introduction", "order_index": 0},
            {"title": "Literature Review", "section_type": "literature_review", "order_index": 1},
            {"title": "Methodology", "section_type": "methods", "order_index": 2},
            {"title": "Results", "section_type": "results", "order_index": 3},
            {"title": "Discussion", "section_type": "discussion", "order_index": 4},
            {"title": "Conclusion", "section_type": "conclusion", "order_index": 5},
        ]
        
        created_sections = []
        for section in sections:
            result = db.table("outline_section").insert({
                "project_id": request.project_id,
                **section,
            }).execute()
            
            if result.data:
                created_sections.append(result.data[0]["title"])
        
        return GenerateOutlineResponse(
            project_id=request.project_id,
            sections_created=len(created_sections),
            section_titles=created_sections,
        )
        
    except Exception as e:
        logger.exception(f"Test harness error generating outline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/full-research-flow",
    response_model=FullResearchFlowResponse,
    summary="Run complete research flow",
    description="Execute a complete research workflow: create project, search, ingest, outline.",
)
async def full_research_flow_test(
    request: FullResearchFlowRequest,
    user: CurrentUser,
    db: DatabaseDep,
) -> FullResearchFlowResponse:
    """Execute complete research workflow for testing."""
    import time
    start = time.time()
    steps_completed = []
    
    try:
        # Step 1: Create project
        project_title = f"Research: {request.topic[:50]}"
        project_result = db.table("project").insert({
            "title": project_title,
            "description": f"Auto-generated research on: {request.topic}",
            "status": ProjectStatus.DRAFT.value,
        }).execute()
        
        if not project_result.data:
            raise HTTPException(status_code=500, detail="Failed to create project")
        
        project_id = project_result.data[0]["id"]
        steps_completed.append("project_created")
        
        # Step 2: Search for papers
        papers_found = 0
        try:
            from src.services.semantic_scholar import search_papers
            papers = await search_papers(request.topic, limit=request.num_papers)
            papers_found = len(papers)
            steps_completed.append("papers_searched")
        except Exception as e:
            logger.warning(f"Paper search failed: {e}")
            papers = []
        
        # Step 3: Add sources (simulate ingestion)
        papers_ingested = 0
        for paper in papers[:request.num_papers]:
            try:
                db.table("source").insert({
                    "project_id": project_id,
                    "paper_id": paper.get("paperId"),
                    "title": paper.get("title", "Unknown"),
                    "authors": [{"name": a.get("name", "")} for a in paper.get("authors", [])[:5]],
                    "abstract": paper.get("abstract"),
                    "year": paper.get("year"),
                    "ingestion_status": "pending",
                }).execute()
                papers_ingested += 1
            except Exception as e:
                logger.warning(f"Failed to add source: {e}")
        
        if papers_ingested > 0:
            steps_completed.append("sources_added")
        
        # Step 4: Generate outline
        outline_sections = 0
        if request.generate_outline:
            sections = [
                {"title": "Introduction", "section_type": "introduction", "order_index": 0},
                {"title": f"Background: {request.topic[:30]}", "section_type": "literature_review", "order_index": 1},
                {"title": "Key Findings", "section_type": "results", "order_index": 2},
                {"title": "Conclusion", "section_type": "conclusion", "order_index": 3},
            ]
            
            for section in sections:
                try:
                    db.table("outline_section").insert({
                        "project_id": project_id,
                        **section,
                    }).execute()
                    outline_sections += 1
                except Exception as e:
                    logger.warning(f"Failed to create section: {e}")
            
            if outline_sections > 0:
                steps_completed.append("outline_generated")
        
        execution_time = (time.time() - start) * 1000
        
        return FullResearchFlowResponse(
            project_id=project_id,
            project_title=project_title,
            papers_found=papers_found,
            papers_ingested=papers_ingested,
            outline_sections=outline_sections,
            execution_time_ms=execution_time,
            steps_completed=steps_completed,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Test harness full flow error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/diagnostics",
    response_model=DiagnosticsResponse,
    summary="Get system diagnostics",
    description="Get detailed system health and diagnostic information.",
)
async def get_test_diagnostics(
    db: DatabaseDep,
) -> DiagnosticsResponse:
    """Get system diagnostics for debugging."""
    settings = get_settings()
    
    # Check database
    db_connected = await check_database_connection()
    
    # Check LightRAG (simple connectivity test)
    lightrag_available = False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.lightrag_url}/health")
            lightrag_available = response.status_code == 200
    except Exception:
        pass
    
    # Count projects
    active_projects = 0
    try:
        result = db.table("project").select("id", count="exact").execute()
        active_projects = result.count or 0
    except Exception:
        pass
    
    # Overall status
    if db_connected and lightrag_available:
        backend_status = "healthy"
    elif db_connected:
        backend_status = "degraded"
    else:
        backend_status = "unhealthy"
    
    return DiagnosticsResponse(
        timestamp=datetime.utcnow(),
        backend_status=backend_status,
        database_connected=db_connected,
        lightrag_available=lightrag_available,
        recent_errors=[],  # TODO: Implement error log collection
        request_count=0,  # TODO: Implement request counting
        active_projects=active_projects,
        environment=settings.environment,
    )


@router.delete(
    "/cleanup/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cleanup test project",
    description="Delete a test project and all associated data.",
)
async def cleanup_test_project(
    project_id: str,
    user: CurrentUser,
    db: DatabaseDep,
) -> None:
    """Delete a test project and its data."""
    try:
        # Delete in order due to foreign keys
        db.table("outline_section").delete().eq("project_id", project_id).execute()
        db.table("source").delete().eq("project_id", project_id).execute()
        db.table("project").delete().eq("id", project_id).execute()
        
        logger.info(f"Test harness cleaned up project: {project_id}")
        
    except Exception as e:
        logger.exception(f"Test harness cleanup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

