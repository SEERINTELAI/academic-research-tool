"""
Models for Chat-Driven Research UI.
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Chat Messages
# ============================================================================

class ChatRole(str, Enum):
    """Chat message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessageCreate(BaseModel):
    """Create a chat message."""
    content: str = Field(..., min_length=1, max_length=10000)
    metadata: dict = Field(default_factory=dict)


class ChatMessage(BaseModel):
    """Chat message response."""
    id: UUID
    session_id: UUID
    role: ChatRole
    content: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    message: str = Field(..., min_length=1, max_length=5000)


class ChatResponse(BaseModel):
    """Response from chat message processing."""
    message: str
    action_taken: Optional[str] = None
    papers_added: list[int] = Field(default_factory=list)
    papers_referenced: list[int] = Field(default_factory=list)
    sections_created: int = 0
    claims_created: int = 0
    metadata: dict = Field(default_factory=dict)


# ============================================================================
# Paper List (for Explore Tab)
# ============================================================================

class PaperAuthor(BaseModel):
    """Paper author."""
    name: str
    affiliation: Optional[str] = None


class PaperListItem(BaseModel):
    """Paper item for the Explore tab list."""
    index: int  # Display index for referencing (e.g., "#5")
    paper_id: str
    node_id: UUID
    source_id: Optional[UUID] = None
    
    title: str
    authors: list[PaperAuthor] = Field(default_factory=list)
    year: Optional[int] = None
    summary: str = ""  # One-line summary
    
    citation_count: Optional[int] = None
    relevance_score: float = 0.0
    user_rating: Optional[str] = None
    
    is_ingested: bool = False
    pdf_url: Optional[str] = None


class PaperDetails(BaseModel):
    """Full paper details for the details panel."""
    index: int
    paper_id: str
    node_id: UUID
    source_id: Optional[UUID] = None
    
    title: str
    authors: list[PaperAuthor] = Field(default_factory=list)
    year: Optional[int] = None
    abstract: str = ""
    
    venue: Optional[str] = None
    doi: Optional[str] = None
    citation_count: Optional[int] = None
    
    pdf_url: Optional[str] = None
    is_ingested: bool = False
    ingestion_status: Optional[str] = None
    
    user_rating: Optional[str] = None
    user_note: Optional[str] = None


# ============================================================================
# Outline with Sources (for Outline Tab)
# ============================================================================

class SourceBadge(BaseModel):
    """Source reference badge for claims."""
    index: int  # Paper display index
    paper_id: str
    title: str
    confidence: float = 0.5


class ClaimWithSources(BaseModel):
    """Claim with source badges for the outline tab."""
    id: UUID
    claim_text: str
    order_index: int
    
    sources: list[SourceBadge] = Field(default_factory=list)
    evidence_strength: str = "moderate"
    needs_sources: bool = False
    
    user_critique: Optional[str] = None
    status: str = "draft"


class SectionWithClaims(BaseModel):
    """Section with claims for the outline tab."""
    id: UUID
    title: str
    section_type: str
    order_index: int
    
    claims: list[ClaimWithSources] = Field(default_factory=list)
    
    # Aggregate stats
    total_claims: int = 0
    claims_with_sources: int = 0
    claims_needing_sources: int = 0


class OutlineWithSources(BaseModel):
    """Full outline with source information."""
    project_id: UUID
    session_id: UUID
    
    sections: list[SectionWithClaims] = Field(default_factory=list)
    
    # Summary stats
    total_sections: int = 0
    total_claims: int = 0
    claims_with_sources: int = 0
    claims_needing_sources: int = 0


# ============================================================================
# Knowledge Tree (for Knowledge Tree Tab)
# ============================================================================

class TreeNode(BaseModel):
    """Node for the knowledge tree visualization."""
    id: str  # UUID as string for graph library compatibility
    label: str  # Short label for display on node
    title: str  # Full title for tooltip
    
    node_type: str  # topic, source, claim, etc.
    year: Optional[int] = None
    
    # For visualization
    size: int = 10  # Node size
    color: Optional[str] = None  # Topic cluster color
    
    # Paper index if this is a source node
    paper_index: Optional[int] = None
    
    # User feedback
    user_rating: Optional[str] = None


class TreeEdge(BaseModel):
    """Edge for the knowledge tree visualization."""
    source: str  # Source node ID
    target: str  # Target node ID
    relationship: str = "related"  # parent, cites, similar, etc.


class KnowledgeTreeGraph(BaseModel):
    """Knowledge tree for graph visualization."""
    session_id: UUID
    topic: str
    
    nodes: list[TreeNode] = Field(default_factory=list)
    edges: list[TreeEdge] = Field(default_factory=list)
    
    # Stats
    total_papers: int = 0
    total_topics: int = 0


# ============================================================================
# Session Info
# ============================================================================

class ResearchSessionInfo(BaseModel):
    """Research session info for the UI."""
    id: UUID
    project_id: UUID
    topic: str
    status: str
    
    papers_found: int = 0
    papers_ingested: int = 0
    outline_sections: int = 0
    
    created_at: datetime
    updated_at: datetime

