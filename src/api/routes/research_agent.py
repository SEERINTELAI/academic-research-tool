"""
API routes for AI Research Agent.

Provides endpoints for:
- Research session management
- Topic exploration
- Knowledge tree operations
- Outline generation from knowledge
- User feedback/critique handling
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.api.deps import CurrentUser, DatabaseDep
from src.models.knowledge import (
    CritiqueRequest,
    DeepenRequest,
    ExploreRequest,
    ExploreResult,
    GenerateOutlineRequest,
    GenerateOutlineResult,
    KnowledgeNode,
    KnowledgeNodeUpdate,
    KnowledgeTree,
    OutlineClaim,
    ResearchSession,
    ResearchSessionCreate,
    ResearchSessionUpdate,
)
from src.services.research_agent import ResearchAgent, ResearchAgentError

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Research Session
# ============================================================================

@router.post(
    "/session",
    response_model=ResearchSession,
    status_code=status.HTTP_201_CREATED,
    summary="Start research session",
)
async def start_session(
    project_id: UUID,
    data: ResearchSessionCreate,
    user: CurrentUser,
    db: DatabaseDep,
) -> ResearchSession:
    """
    Start a new research session for a project.
    
    The AI will begin exploring the given topic.
    """
    try:
        agent = ResearchAgent(project_id)
        session = await agent.start_session(data.topic, data.guidance_notes)
        return session
    except ResearchAgentError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get(
    "/session",
    response_model=Optional[ResearchSession],
    summary="Get current session",
)
async def get_session(
    project_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
) -> Optional[ResearchSession]:
    """Get the current research session for a project."""
    agent = ResearchAgent(project_id)
    return await agent.get_session()


@router.patch(
    "/session",
    response_model=ResearchSession,
    summary="Update session",
)
async def update_session(
    project_id: UUID,
    data: ResearchSessionUpdate,
    user: CurrentUser,
    db: DatabaseDep,
) -> ResearchSession:
    """Update the research session (topic, guidance, status)."""
    agent = ResearchAgent(project_id)
    session = await agent.get_session()
    if not session:
        raise HTTPException(status_code=404, detail="No active session")
    
    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        result = db.table("research_session")\
            .update(update_data)\
            .eq("id", str(session.id))\
            .execute()
        if result.data:
            return ResearchSession(**result.data[0])
    
    return session


# ============================================================================
# Exploration
# ============================================================================

@router.post(
    "/explore",
    response_model=ExploreResult,
    summary="Explore topic",
)
async def explore_topic(
    project_id: UUID,
    data: ExploreRequest,
    user: CurrentUser,
    db: DatabaseDep,
) -> ExploreResult:
    """
    Explore a topic - search for papers and auto-ingest.
    
    The AI will:
    1. Search academic databases
    2. Filter by relevance
    3. Auto-ingest promising papers
    4. Generate summaries
    5. Suggest subtopics
    """
    agent = ResearchAgent(project_id)
    session = await agent.get_session()
    if not session:
        raise HTTPException(status_code=404, detail="No active session. Start one first.")
    
    try:
        return await agent.explore(data)
    except ResearchAgentError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post(
    "/deepen",
    response_model=ExploreResult,
    summary="Go deeper on subtopic",
)
async def deepen_topic(
    project_id: UUID,
    data: DeepenRequest,
    user: CurrentUser,
    db: DatabaseDep,
) -> ExploreResult:
    """
    Go deeper on a specific subtopic.
    
    Creates a sub-branch in the knowledge tree.
    """
    agent = ResearchAgent(project_id)
    session = await agent.get_session()
    if not session:
        raise HTTPException(status_code=404, detail="No active session")
    
    try:
        return await agent.deepen(data)
    except ResearchAgentError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post(
    "/suggest",
    response_model=ExploreResult,
    summary="Suggest direction",
)
async def suggest_direction(
    project_id: UUID,
    suggestion: str = Query(..., min_length=3),
    user: CurrentUser = None,
    db: DatabaseDep = None,
) -> ExploreResult:
    """
    Suggest a new direction for research.
    
    User provides a suggestion and AI explores that direction.
    """
    agent = ResearchAgent(project_id)
    session = await agent.get_session()
    if not session:
        raise HTTPException(status_code=404, detail="No active session")
    
    try:
        return await agent.suggest_direction(suggestion)
    except ResearchAgentError as e:
        raise HTTPException(status_code=400, detail=e.message)


# ============================================================================
# Knowledge Tree
# ============================================================================

@router.get(
    "/knowledge",
    response_model=KnowledgeTree,
    summary="Get knowledge tree",
)
async def get_knowledge_tree(
    project_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
) -> KnowledgeTree:
    """
    Get the full knowledge tree for the current session.
    
    Returns all nodes organized hierarchically.
    """
    agent = ResearchAgent(project_id)
    session = await agent.get_session()
    if not session:
        raise HTTPException(status_code=404, detail="No active session")
    
    try:
        return await agent.get_knowledge_tree()
    except ResearchAgentError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.patch(
    "/knowledge/{node_id}",
    response_model=KnowledgeNode,
    summary="Update knowledge node",
)
async def update_knowledge_node(
    project_id: UUID,
    node_id: UUID,
    data: KnowledgeNodeUpdate,
    user: CurrentUser,
    db: DatabaseDep,
) -> KnowledgeNode:
    """
    Update a knowledge node (rating, notes, visibility).
    """
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    result = db.table("knowledge_node")\
        .update(update_data)\
        .eq("id", str(node_id))\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Node not found")
    
    return KnowledgeNode(**result.data[0])


@router.post(
    "/knowledge/{node_id}/rate",
    response_model=KnowledgeNode,
    summary="Rate knowledge node",
)
async def rate_node(
    project_id: UUID,
    node_id: UUID,
    rating: str = Query(..., pattern="^(useful|neutral|irrelevant)$"),
    note: Optional[str] = Query(None),
    user: CurrentUser = None,
    db: DatabaseDep = None,
) -> KnowledgeNode:
    """
    Rate a knowledge node as useful, neutral, or irrelevant.
    
    Irrelevant nodes are hidden from the tree.
    """
    agent = ResearchAgent(project_id)
    try:
        return await agent.rate_node(node_id, rating, note)
    except ResearchAgentError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.delete(
    "/knowledge/{node_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete knowledge node",
)
async def delete_knowledge_node(
    project_id: UUID,
    node_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
):
    """Delete a knowledge node (and its children)."""
    result = db.table("knowledge_node")\
        .delete()\
        .eq("id", str(node_id))\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Node not found")


# ============================================================================
# Outline Generation
# ============================================================================

@router.post(
    "/generate-outline",
    response_model=GenerateOutlineResult,
    summary="Generate outline from knowledge",
)
async def generate_outline(
    project_id: UUID,
    data: Optional[GenerateOutlineRequest] = None,
    user: CurrentUser = None,
    db: DatabaseDep = None,
) -> GenerateOutlineResult:
    """
    Generate an outline from the accumulated knowledge.
    
    The AI will:
    1. Cluster knowledge nodes into themes
    2. Create outline sections
    3. Generate claims with source links
    """
    agent = ResearchAgent(project_id)
    session = await agent.get_session()
    if not session:
        raise HTTPException(status_code=404, detail="No active session")
    
    try:
        return await agent.generate_outline(data)
    except ResearchAgentError as e:
        raise HTTPException(status_code=400, detail=e.message)


# ============================================================================
# Claims & Critique
# ============================================================================

@router.get(
    "/claims",
    response_model=list[OutlineClaim],
    summary="Get all claims with sources",
)
async def get_claims(
    project_id: UUID,
    section_id: Optional[UUID] = Query(None),
    user: CurrentUser = None,
    db: DatabaseDep = None,
) -> list[OutlineClaim]:
    """
    Get outline claims with their source links.
    
    Optionally filter by section.
    """
    query = db.table("outline_claim").select("*")
    
    if section_id:
        query = query.eq("section_id", str(section_id))
    else:
        # Join to get claims for this project's sections
        # Simplified - just get all claims for now
        pass
    
    query = query.order("order_index")
    result = query.execute()
    
    return [OutlineClaim(**row) for row in result.data]


@router.post(
    "/claims/{claim_id}/critique",
    summary="Critique a claim",
)
async def critique_claim(
    project_id: UUID,
    claim_id: UUID,
    data: CritiqueRequest,
    user: CurrentUser = None,
    db: DatabaseDep = None,
) -> dict:
    """
    Submit a critique of a claim.
    
    Critique types:
    - needs_more_sources: AI finds more supporting papers
    - irrelevant: Removes the claim
    - expand: AI creates sub-claims with more detail
    - merge: Merge with another claim
    - split: Split into multiple claims
    """
    agent = ResearchAgent(project_id)
    try:
        return await agent.handle_critique(claim_id, data)
    except ResearchAgentError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.patch(
    "/claims/{claim_id}",
    response_model=OutlineClaim,
    summary="Update claim",
)
async def update_claim(
    project_id: UUID,
    claim_id: UUID,
    claim_text: Optional[str] = None,
    user_critique: Optional[str] = None,
    status: Optional[str] = None,
    user: CurrentUser = None,
    db: DatabaseDep = None,
) -> OutlineClaim:
    """Update a claim's text, critique, or status."""
    update_data = {}
    if claim_text:
        update_data["claim_text"] = claim_text
    if user_critique:
        update_data["user_critique"] = user_critique
    if status:
        update_data["status"] = status
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data")
    
    result = db.table("outline_claim")\
        .update(update_data)\
        .eq("id", str(claim_id))\
        .execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    return OutlineClaim(**result.data[0])

