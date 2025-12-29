"""
Models for AI Research Assistant: Knowledge Tree and Research Sessions.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================

class SessionStatus(str, Enum):
    """Research session status."""
    EXPLORING = "exploring"
    DRAFTING = "drafting"
    REFINING = "refining"
    COMPLETED = "completed"


class NodeType(str, Enum):
    """Knowledge node types."""
    TOPIC = "topic"
    SOURCE = "source"
    CLAIM = "claim"
    SUMMARY = "summary"
    QUESTION = "question"


class UserRating(str, Enum):
    """User rating for knowledge nodes."""
    USEFUL = "useful"
    NEUTRAL = "neutral"
    IRRELEVANT = "irrelevant"


class EvidenceStrength(str, Enum):
    """Evidence strength for claims."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NEEDS_MORE = "needs_more"
    NONE = "none"


class ClaimStatus(str, Enum):
    """Claim review status."""
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"


# ============================================================================
# Research Session
# ============================================================================

class ResearchSessionCreate(BaseModel):
    """Create a new research session."""
    topic: str = Field(..., min_length=3, max_length=500)
    guidance_notes: Optional[str] = None


class ResearchSessionUpdate(BaseModel):
    """Update research session."""
    topic: Optional[str] = None
    status: Optional[SessionStatus] = None
    guidance_notes: Optional[str] = None


class ResearchSession(BaseModel):
    """Research session response."""
    id: UUID
    project_id: UUID
    topic: str
    status: SessionStatus
    guidance_notes: Optional[str] = None
    sources_ingested: int = 0
    nodes_created: int = 0
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Knowledge Node
# ============================================================================

class KnowledgeNodeCreate(BaseModel):
    """Create a knowledge node."""
    parent_node_id: Optional[UUID] = None
    source_id: Optional[UUID] = None
    node_type: NodeType
    title: str = Field(..., min_length=1, max_length=500)
    content: Optional[str] = None
    confidence: float = Field(0.5, ge=0, le=1)
    relevance_score: float = Field(0.5, ge=0, le=1)


class KnowledgeNodeUpdate(BaseModel):
    """Update a knowledge node."""
    title: Optional[str] = None
    content: Optional[str] = None
    user_rating: Optional[UserRating] = None
    user_note: Optional[str] = None
    is_hidden: Optional[bool] = None


class KnowledgeNode(BaseModel):
    """Knowledge node response."""
    id: UUID
    session_id: UUID
    source_id: Optional[UUID] = None
    parent_node_id: Optional[UUID] = None
    
    node_type: NodeType
    title: str
    content: Optional[str] = None
    
    confidence: float
    relevance_score: float
    
    user_rating: Optional[UserRating] = None
    user_note: Optional[str] = None
    is_hidden: bool = False
    
    order_index: int = 0
    created_at: datetime
    
    # For tree building
    children: list["KnowledgeNode"] = []


class KnowledgeTree(BaseModel):
    """Full knowledge tree for a session."""
    session_id: UUID
    topic: str
    nodes: list[KnowledgeNode]
    total_nodes: int
    total_sources: int


# ============================================================================
# Outline Claim
# ============================================================================

class OutlineClaimCreate(BaseModel):
    """Create an outline claim."""
    section_id: UUID
    claim_text: str = Field(..., min_length=5, max_length=2000)
    supporting_nodes: list[UUID] = []
    order_index: int = 0


class OutlineClaimUpdate(BaseModel):
    """Update an outline claim."""
    claim_text: Optional[str] = None
    supporting_nodes: Optional[list[UUID]] = None
    user_critique: Optional[str] = None
    status: Optional[ClaimStatus] = None
    order_index: Optional[int] = None


class OutlineClaim(BaseModel):
    """Outline claim response."""
    id: UUID
    section_id: UUID
    claim_text: str
    order_index: int
    
    supporting_nodes: list[UUID] = []
    evidence_strength: EvidenceStrength = EvidenceStrength.MODERATE
    source_count: int = 0
    
    user_critique: Optional[str] = None
    status: ClaimStatus = ClaimStatus.DRAFT
    suggested_action: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime


class OutlineClaimWithSources(OutlineClaim):
    """Claim with expanded source information."""
    sources: list[KnowledgeNode] = []


# ============================================================================
# Exploration Actions
# ============================================================================

class ExploreRequest(BaseModel):
    """Request to explore a topic."""
    topic: Optional[str] = None  # If None, uses session topic
    guidance: Optional[str] = None  # User guidance
    max_papers: int = Field(10, ge=1, le=50)
    auto_ingest: bool = True


class DeepenRequest(BaseModel):
    """Request to go deeper on a subtopic."""
    subtopic: str
    parent_node_id: Optional[UUID] = None
    guidance: Optional[str] = None
    max_papers: int = Field(5, ge=1, le=20)


class CritiqueRequest(BaseModel):
    """User critique of a claim."""
    critique_type: str = Field(..., pattern="^(needs_more_sources|irrelevant|expand|merge|split)$")
    details: Optional[str] = None
    target_node_ids: list[UUID] = []


class ExploreResult(BaseModel):
    """Result of exploration."""
    papers_found: int
    papers_ingested: int
    nodes_created: int
    summaries: list[str]
    suggested_subtopics: list[str]
    exploration_log_id: UUID


class GenerateOutlineRequest(BaseModel):
    """Request to generate outline from knowledge."""
    focus_nodes: list[UUID] = []  # Specific nodes to focus on (empty = all)
    max_sections: int = Field(10, ge=1, le=50)
    depth: int = Field(2, ge=1, le=5)  # Heading depth


class GenerateOutlineResult(BaseModel):
    """Result of outline generation."""
    sections_created: int
    claims_created: int
    outline_summary: str

