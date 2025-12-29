"""
Integration tests for the chat-driven research workflow.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services.research_agent import ResearchAgent
from src.models.chat import ChatResponse, PaperListItem
from src.models.knowledge import (
    ResearchSession,
    SessionStatus,
    ExploreResult,
    KnowledgeTree,
    KnowledgeNode,
    NodeType,
)


@pytest.fixture
def mock_db():
    """Create a mock database client."""
    db = MagicMock()
    
    # Mock table operations
    def mock_table(name):
        table = MagicMock()
        table.insert.return_value.execute.return_value = MagicMock(data=[{
            "id": str(uuid4()),
            "session_id": str(uuid4()),
            "project_id": str(uuid4()),
            "topic": "test topic",
            "status": "exploring",
            "sources_ingested": 0,
            "nodes_created": 0,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }])
        table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        table.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(data=[])
        table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        return table
    
    db.table = mock_table
    return db


@pytest.fixture
def research_agent(mock_db):
    """Create a research agent with mocked dependencies."""
    with patch('src.services.research_agent.get_supabase_client', return_value=mock_db):
        agent = ResearchAgent(project_id=uuid4())
        return agent


class TestProcessMessage:
    """Tests for chat message processing."""

    @pytest.mark.asyncio
    async def test_process_search_message(self, research_agent, mock_db):
        """Test processing a search message."""
        # Setup mock session
        with patch.object(research_agent, 'get_session', new_callable=AsyncMock) as mock_session:
            mock_session.return_value = ResearchSession(
                id=uuid4(),
                project_id=research_agent.project_id,
                topic="quantum computing",
                status=SessionStatus.EXPLORING,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            )
            
            with patch.object(research_agent, 'explore', new_callable=AsyncMock) as mock_explore:
                mock_explore.return_value = ExploreResult(
                    papers_found=10,
                    papers_ingested=5,
                    nodes_created=5,
                    summaries=["Summary 1", "Summary 2"],
                    suggested_subtopics=["subtopic1", "subtopic2"],
                    exploration_log_id=uuid4(),
                )
                
                with patch.object(research_agent, 'get_papers_list', new_callable=AsyncMock) as mock_papers:
                    mock_papers.return_value = [
                        PaperListItem(
                            index=i,
                            paper_id=f"paper_{i}",
                            node_id=uuid4(),
                            source_id=uuid4(),
                            title=f"Paper {i}",
                            authors=[],
                            year=2024,
                            summary="Test summary",
                            citation_count=10,
                            relevance_score=0.8,
                            user_rating=None,
                            is_ingested=True,
                            pdf_url=None,
                        )
                        for i in range(1, 6)
                    ]
                    
                    with patch.object(research_agent, '_save_chat_message', new_callable=AsyncMock):
                        response = await research_agent.process_message("search for quantum cryptography")
                        
                        assert response.action_taken == "search"
                        assert "found" in response.message.lower()
                        assert len(response.papers_added) > 0

    @pytest.mark.asyncio
    async def test_process_message_without_session(self, research_agent):
        """Test processing message when no session exists - should auto-start."""
        with patch.object(research_agent, 'get_session', new_callable=AsyncMock) as mock_session:
            mock_session.return_value = None
            
            with patch.object(research_agent, 'start_session', new_callable=AsyncMock) as mock_start:
                mock_start.return_value = ResearchSession(
                    id=uuid4(),
                    project_id=research_agent.project_id,
                    topic="quantum cryptography",
                    status=SessionStatus.EXPLORING,
                    created_at="2024-01-01T00:00:00Z",
                    updated_at="2024-01-01T00:00:00Z",
                )
                
                with patch.object(research_agent, 'explore', new_callable=AsyncMock) as mock_explore:
                    mock_explore.return_value = ExploreResult(
                        papers_found=5,
                        papers_ingested=3,
                        nodes_created=3,
                        summaries=[],
                        suggested_subtopics=[],
                        exploration_log_id=uuid4(),
                    )
                    
                    with patch.object(research_agent, 'get_papers_list', new_callable=AsyncMock) as mock_papers:
                        mock_papers.return_value = []
                        
                        with patch.object(research_agent, '_save_chat_message', new_callable=AsyncMock):
                            response = await research_agent.process_message("search for quantum cryptography")
                            
                            # Should have auto-started session
                            mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_outline_generation(self, research_agent):
        """Test processing outline generation request."""
        with patch.object(research_agent, 'get_session', new_callable=AsyncMock) as mock_session:
            mock_session.return_value = ResearchSession(
                id=uuid4(),
                project_id=research_agent.project_id,
                topic="quantum computing",
                status=SessionStatus.EXPLORING,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            )
            
            with patch.object(research_agent, 'generate_outline', new_callable=AsyncMock) as mock_outline:
                from src.models.knowledge import GenerateOutlineResult
                mock_outline.return_value = GenerateOutlineResult(
                    sections_created=5,
                    claims_created=15,
                    outline_summary="Created outline",
                )
                
                with patch.object(research_agent, '_save_chat_message', new_callable=AsyncMock):
                    response = await research_agent.process_message("generate an outline")
                    
                    assert response.action_taken == "generate_outline"
                    assert response.sections_created == 5
                    assert response.claims_created == 15


class TestGetPapersList:
    """Tests for papers list retrieval."""

    @pytest.mark.asyncio
    async def test_get_papers_list_empty_session(self, research_agent):
        """Get papers list with no session."""
        with patch.object(research_agent, 'get_session', new_callable=AsyncMock) as mock_session:
            mock_session.return_value = None
            
            papers = await research_agent.get_papers_list()
            assert papers == []


class TestGetOutlineWithSources:
    """Tests for outline with sources retrieval."""

    @pytest.mark.asyncio
    async def test_get_outline_empty(self, research_agent):
        """Get outline when no session exists."""
        with patch.object(research_agent, 'get_session', new_callable=AsyncMock) as mock_session:
            mock_session.return_value = None
            
            outline = await research_agent.get_outline_with_sources()
            assert outline.total_sections == 0


class TestIntentHandlers:
    """Tests for individual intent handlers."""

    @pytest.mark.asyncio
    async def test_handle_find_gaps(self, research_agent):
        """Test finding gaps in claims."""
        with patch.object(research_agent, 'get_session', new_callable=AsyncMock) as mock_session:
            mock_session.return_value = ResearchSession(
                id=uuid4(),
                project_id=research_agent.project_id,
                topic="test",
                status=SessionStatus.EXPLORING,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            )
            
            with patch.object(research_agent, 'get_outline_with_sources', new_callable=AsyncMock) as mock_outline:
                from src.models.chat import OutlineWithSources, SectionWithClaims, ClaimWithSources
                
                mock_outline.return_value = OutlineWithSources(
                    project_id=research_agent.project_id,
                    session_id=uuid4(),
                    sections=[
                        SectionWithClaims(
                            id=uuid4(),
                            title="Introduction",
                            section_type="introduction",
                            order_index=0,
                            claims=[
                                ClaimWithSources(
                                    id=uuid4(),
                                    claim_text="Test claim without sources",
                                    order_index=0,
                                    sources=[],
                                    evidence_strength="none",
                                    needs_sources=True,
                                    user_critique=None,
                                    status="draft",
                                )
                            ],
                            total_claims=1,
                            claims_with_sources=0,
                            claims_needing_sources=1,
                        )
                    ],
                    total_sections=1,
                    total_claims=1,
                    claims_with_sources=0,
                    claims_needing_sources=1,
                )
                
                with patch.object(research_agent, '_save_chat_message', new_callable=AsyncMock):
                    response = await research_agent.process_message("which claims need sources?")
                    
                    assert response.action_taken == "find_gaps"
                    assert "1" in response.message  # Should mention gap count

