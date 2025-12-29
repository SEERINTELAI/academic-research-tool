"""
Chat API endpoints for research UI.

Provides chat-driven research interface endpoints.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.api.deps import CurrentUser, DatabaseDep
from src.models.chat import (
    Author,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    KnowledgeTreeGraph,
    LibraryPaper,
    LibraryResponse,
    OutlineWithSources,
    PaperDetails,
    PaperListItem,
    ResearchSessionInfo,
    TopicGroup,
)
from src.services.research_agent import ResearchAgent, ResearchAgentError

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# Chat Endpoints
# ============================================================================

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a chat message",
    description="Process a user message and return AI response with action taken.",
)
async def send_message(
    project_id: UUID,
    request: ChatRequest,
    user: CurrentUser,
    db: DatabaseDep,
) -> ChatResponse:
    """
    Send a message to the research AI.
    
    The AI will parse intent and perform actions like:
    - Search for papers
    - Find more papers like specific ones
    - Generate outline
    - Link sources to claims
    """
    try:
        agent = ResearchAgent(project_id, auto_ingest=request.auto_ingest)
        response = await agent.process_message(request.message)
        return response
    except ResearchAgentError as e:
        logger.warning(f"Research agent error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except Exception as e:
        logger.exception(f"Error processing chat message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/chat/history",
    response_model=list[ChatMessage],
    summary="Get chat history",
    description="Get conversation history for the research session.",
)
async def get_chat_history(
    project_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
    limit: int = 50,
) -> list[ChatMessage]:
    """Get chat history for the current session."""
    try:
        agent = ResearchAgent(project_id)
        return await agent.get_chat_history(limit)
    except Exception as e:
        logger.exception(f"Error getting chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Paper Endpoints (for Explore Tab)
# ============================================================================

@router.get(
    "/papers",
    response_model=list[PaperListItem],
    summary="Get papers list",
    description="Get indexed list of papers for the Explore tab.",
)
async def get_papers_list(
    project_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
) -> list[PaperListItem]:
    """
    Get papers with display indices.
    
    Each paper has an index for easy referencing in chat (e.g., "paper #5").
    """
    try:
        agent = ResearchAgent(project_id)
        return await agent.get_papers_list()
    except Exception as e:
        logger.exception(f"Error getting papers list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/papers/{index}",
    response_model=PaperDetails,
    summary="Get paper details",
    description="Get full details for a paper by its display index.",
)
async def get_paper_details(
    project_id: UUID,
    index: int,
    user: CurrentUser,
    db: DatabaseDep,
) -> PaperDetails:
    """Get full paper details by display index."""
    try:
        agent = ResearchAgent(project_id)
        details = await agent.get_paper_details(index)
        
        if not details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Paper #{index} not found",
            )
        
        return details
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting paper details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Library Endpoints (for Library Tab - Zotero-like view)
# ============================================================================

@router.get(
    "/library",
    response_model=LibraryResponse,
    summary="Get library grouped by topic",
    description="Get ingested papers grouped by AI-detected topics for Zotero-like view.",
)
async def get_library(
    project_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
) -> LibraryResponse:
    """
    Get library of ingested papers grouped by topic.
    
    Papers are classified by AI into topics like "Machine Learning", 
    "Quantum Computing", etc. for easy browsing.
    """
    try:
        # Get all sources for this project that are ingested
        result = db.table("source")\
            .select("*")\
            .eq("project_id", str(project_id))\
            .eq("ingestion_status", "ready")\
            .order("topic")\
            .execute()
        
        sources = result.data or []
        
        # Group by topic
        topic_map: dict[str, list[LibraryPaper]] = {}
        for source in sources:
            topic = source.get("topic") or "Uncategorized"
            
            if topic not in topic_map:
                topic_map[topic] = []
            
            # Parse authors
            authors_raw = source.get("authors") or []
            authors = [
                Author(name=a.get("name", "Unknown") if isinstance(a, dict) else str(a))
                for a in authors_raw
            ]
            
            paper = LibraryPaper(
                id=source["id"],
                title=source.get("title", "Unknown"),
                authors=authors,
                year=source.get("publication_year"),
                topic=topic,
                topic_confidence=source.get("topic_confidence", 0.0),
                doi=source.get("doi"),
                journal=source.get("journal"),
                citation_count=source.get("citation_count"),
                ingestion_status=source.get("ingestion_status", "pending"),
                ingested_at=source.get("updated_at"),
            )
            topic_map[topic].append(paper)
        
        # Build response
        topics = [
            TopicGroup(
                topic=topic_name,
                paper_count=len(papers),
                papers=papers,
            )
            for topic_name, papers in sorted(topic_map.items())
        ]
        
        total_papers = sum(len(papers) for papers in topic_map.values())
        
        return LibraryResponse(
            project_id=project_id,
            topics=topics,
            total_papers=total_papers,
            total_topics=len(topics),
            papers_ingested=total_papers,
            papers_pending=0,  # These are all ingested
        )
    except Exception as e:
        logger.exception(f"Error getting library: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Outline Endpoints (for Outline Tab)
# ============================================================================

@router.get(
    "/outline",
    response_model=OutlineWithSources,
    summary="Get outline with sources",
    description="Get outline with claims and source badges for the Outline tab.",
)
async def get_outline_with_sources(
    project_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
) -> OutlineWithSources:
    """
    Get outline with source information.
    
    Each claim shows which papers support it and which need more sources.
    """
    try:
        agent = ResearchAgent(project_id)
        return await agent.get_outline_with_sources()
    except Exception as e:
        logger.exception(f"Error getting outline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Knowledge Tree Endpoints (for Knowledge Tree Tab)
# ============================================================================

@router.get(
    "/tree",
    response_model=KnowledgeTreeGraph,
    summary="Get knowledge tree",
    description="Get knowledge tree for graph visualization.",
)
async def get_knowledge_tree(
    project_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
) -> KnowledgeTreeGraph:
    """
    Get knowledge tree for visualization.
    
    Returns nodes and edges for a force-directed graph.
    """
    try:
        agent = ResearchAgent(project_id)
        return await agent.get_knowledge_tree_graph()
    except Exception as e:
        logger.exception(f"Error getting knowledge tree: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Session Endpoints
# ============================================================================

@router.get(
    "/session",
    response_model=Optional[ResearchSessionInfo],
    summary="Get current research session",
    description="Get info about the current research session if one exists.",
)
async def get_session(
    project_id: UUID,
    user: CurrentUser,
    db: DatabaseDep,
) -> Optional[ResearchSessionInfo]:
    """Get current research session info."""
    try:
        agent = ResearchAgent(project_id)
        session = await agent.get_session()
        
        if not session:
            return None
        
        # Get stats
        papers = await agent.get_papers_list()
        outline = await agent.get_outline_with_sources()
        
        return ResearchSessionInfo(
            id=session.id,
            project_id=session.project_id,
            topic=session.topic,
            status=session.status.value,
            papers_found=len(papers),
            papers_ingested=len([p for p in papers if p.is_ingested]),
            outline_sections=outline.total_sections,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
    except Exception as e:
        logger.exception(f"Error getting session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

