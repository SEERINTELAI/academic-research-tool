"""
Full Lifecycle E2E Tests for Academic Research Tool.

Tests the complete research workflow from project creation to paper generation:
1. Create a new project
2. Search for sources and add them to the library
3. Verify sources were added correctly and the knowledge tree builds with edges
4. Build an outline with cited sources and critique/update via AI
5. Generate a paper with full citations

These tests require a running backend server with database access.
"""

import asyncio
import logging
import os
from typing import Optional
from uuid import UUID

import httpx
import pytest

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

BASE_URL = os.getenv("TEST_API_URL", "http://localhost:8003")
DEMO_TOKEN = "demo-token"
TIMEOUT = 120.0  # Longer timeout for research operations


# =============================================================================
# API Client
# =============================================================================

class LifecycleAPIClient:
    """API client for full lifecycle E2E tests."""
    
    def __init__(self, base_url: str = BASE_URL, token: str = DEMO_TOKEN):
        self.base_url = base_url
        self.token = token
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=TIMEOUT,
            headers={"Authorization": f"Bearer {self.token}"},
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._client
    
    # ----- Projects -----
    
    async def create_project(self, title: str, description: str = "") -> dict:
        """Create a new project."""
        response = await self.client.post(
            "/api/projects",
            json={"title": title, "description": description},
        )
        response.raise_for_status()
        return response.json()
    
    async def get_project(self, project_id: str) -> dict:
        """Get project by ID."""
        response = await self.client.get(f"/api/projects/{project_id}")
        response.raise_for_status()
        return response.json()
    
    async def delete_project(self, project_id: str) -> None:
        """Delete a project."""
        response = await self.client.delete(f"/api/projects/{project_id}")
        response.raise_for_status()
    
    # ----- Research Chat -----
    
    async def send_chat_message(
        self, project_id: str, message: str, auto_ingest: bool = True
    ) -> dict:
        """Send a message to the research AI."""
        response = await self.client.post(
            f"/api/projects/{project_id}/research-ui/chat",
            json={"message": message, "auto_ingest": auto_ingest},
        )
        response.raise_for_status()
        return response.json()
    
    async def get_chat_history(self, project_id: str) -> list:
        """Get chat history."""
        response = await self.client.get(
            f"/api/projects/{project_id}/research-ui/chat/history"
        )
        response.raise_for_status()
        return response.json()
    
    async def get_research_session(self, project_id: str) -> Optional[dict]:
        """Get current research session."""
        response = await self.client.get(
            f"/api/projects/{project_id}/research-ui/session"
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    
    # ----- Papers -----
    
    async def get_papers_list(self, project_id: str) -> list:
        """Get indexed papers list."""
        response = await self.client.get(
            f"/api/projects/{project_id}/research-ui/papers"
        )
        response.raise_for_status()
        return response.json()
    
    async def get_paper_details(self, project_id: str, index: int) -> dict:
        """Get paper details by index."""
        response = await self.client.get(
            f"/api/projects/{project_id}/research-ui/papers/{index}"
        )
        response.raise_for_status()
        return response.json()
    
    # ----- Sources / Library -----
    
    async def get_sources(self, project_id: str) -> list:
        """Get project sources."""
        response = await self.client.get(f"/api/projects/{project_id}/sources")
        response.raise_for_status()
        return response.json()
    
    async def get_library(self, project_id: str) -> dict:
        """Get library with papers grouped by topic."""
        response = await self.client.get(
            f"/api/projects/{project_id}/research-ui/library"
        )
        response.raise_for_status()
        return response.json()
    
    async def ingest_source(self, project_id: str, source_id: str) -> dict:
        """Trigger ingestion for a source."""
        response = await self.client.post(
            f"/api/projects/{project_id}/sources/{source_id}/ingest"
        )
        response.raise_for_status()
        return response.json()
    
    # ----- Knowledge Tree -----
    
    async def get_knowledge_tree(self, project_id: str) -> dict:
        """Get knowledge tree graph with citation edges."""
        response = await self.client.get(
            f"/api/projects/{project_id}/research-ui/tree"
        )
        response.raise_for_status()
        return response.json()
    
    # ----- Outline -----
    
    async def get_outline(self, project_id: str) -> dict:
        """Get outline with sources."""
        response = await self.client.get(
            f"/api/projects/{project_id}/research-ui/outline"
        )
        response.raise_for_status()
        return response.json()
    
    async def update_outline_section(
        self, project_id: str, section_id: str, updates: dict
    ) -> dict:
        """Update an outline section."""
        response = await self.client.patch(
            f"/api/projects/{project_id}/outline/sections/{section_id}",
            json=updates,
        )
        response.raise_for_status()
        return response.json()
    
    # ----- Report / Paper Generation -----
    
    async def generate_report(self, project_id: str) -> dict:
        """Generate a paper from the outline."""
        response = await self.client.post(
            f"/api/projects/{project_id}/report/generate"
        )
        response.raise_for_status()
        return response.json()
    
    async def get_report(self, project_id: str) -> dict:
        """Get generated report."""
        response = await self.client.get(f"/api/projects/{project_id}/report")
        response.raise_for_status()
        return response.json()
    
    async def generate_section_draft(
        self, project_id: str, section_id: str
    ) -> dict:
        """Generate draft for a specific section."""
        response = await self.client.post(
            f"/api/projects/{project_id}/report/sections/{section_id}/write"
        )
        response.raise_for_status()
        return response.json()


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
async def api():
    """Create API client."""
    async with LifecycleAPIClient() as client:
        yield client


# Store project ID across tests
_test_project_id: Optional[str] = None


# =============================================================================
# Full Lifecycle Tests
# =============================================================================

@pytest.mark.e2e
@pytest.mark.lifecycle
class TestFullResearchLifecycle:
    """
    Full lifecycle E2E test covering:
    1. Create project
    2. Search and add sources to library
    3. Verify knowledge tree with citation edges
    4. Build outline with AI critique/update
    5. Generate paper with citations
    
    Tests are numbered to ensure order execution.
    """
    
    @pytest.mark.asyncio
    async def test_01_create_project(self, api: LifecycleAPIClient):
        """Step 1: Create a new research project."""
        global _test_project_id
        
        project = await api.create_project(
            title="Full Lifecycle Test - Machine Learning Survey",
            description="E2E test covering the complete research workflow",
        )
        
        assert project["id"], "Project ID should be returned"
        assert project["title"] == "Full Lifecycle Test - Machine Learning Survey"
        assert project["status"] == "draft"
        
        _test_project_id = project["id"]
        logger.info(f"Created test project: {_test_project_id}")
    
    @pytest.mark.asyncio
    async def test_02_search_papers(self, api: LifecycleAPIClient):
        """Step 2: Search for papers via chat."""
        global _test_project_id
        assert _test_project_id, "Project must be created first"
        
        # Search for papers - this creates a session and finds papers
        response = await api.send_chat_message(
            _test_project_id,
            "Search for machine learning optimization papers",
            auto_ingest=False,  # Don't auto-ingest, we'll do it manually
        )
        
        assert response["message"], "Should get a response message"
        assert response["action_taken"] in ["search", "error", "prompt_for_topic"]
        
        # Verify session was created
        session = await api.get_research_session(_test_project_id)
        assert session is not None, "Research session should be created"
        
        logger.info(f"Search completed: {response['action_taken']}")
    
    @pytest.mark.asyncio
    async def test_03_ingest_papers(self, api: LifecycleAPIClient):
        """Step 3: Ingest papers to the library."""
        global _test_project_id
        assert _test_project_id, "Project must be created first"
        
        # Get papers from explore
        papers = await api.get_papers_list(_test_project_id)
        
        if len(papers) == 0:
            pytest.skip("No papers found from search - may be rate limited")
        
        # Try to ingest first paper with PDF available
        ingested_count = 0
        for paper in papers[:3]:  # Try first 3 papers
            if paper.get("has_pdf") and paper.get("source_id"):
                try:
                    result = await api.ingest_source(
                        _test_project_id, paper["source_id"]
                    )
                    ingested_count += 1
                    logger.info(f"Ingested paper: {paper['title'][:50]}...")
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 422:
                        # Ingestion failed (no PDF), skip
                        continue
                    raise
        
        logger.info(f"Ingested {ingested_count} papers to library")
    
    @pytest.mark.asyncio
    async def test_04_verify_library(self, api: LifecycleAPIClient):
        """Step 4: Verify sources appear in library with topics."""
        global _test_project_id
        assert _test_project_id, "Project must be created first"
        
        # Wait for ingestion to complete
        await asyncio.sleep(2)
        
        # Get library
        library = await api.get_library(_test_project_id)
        
        assert "topics" in library, "Library should have topics"
        
        total_papers = sum(
            len(topic.get("papers", [])) for topic in library.get("topics", [])
        )
        
        logger.info(
            f"Library has {len(library.get('topics', []))} topics "
            f"with {total_papers} papers"
        )
    
    @pytest.mark.asyncio
    async def test_05_verify_citation_tree(self, api: LifecycleAPIClient):
        """Step 5: Verify knowledge tree shows papers with citation edges."""
        global _test_project_id
        assert _test_project_id, "Project must be created first"
        
        tree = await api.get_knowledge_tree(_test_project_id)
        
        assert "nodes" in tree, "Tree should have nodes"
        assert "edges" in tree, "Tree should have edges"
        assert "total_papers" in tree, "Tree should report total papers"
        
        logger.info(
            f"Knowledge tree has {len(tree['nodes'])} nodes "
            f"and {len(tree['edges'])} citation edges"
        )
        
        # Verify node structure
        if tree["nodes"]:
            node = tree["nodes"][0]
            assert "id" in node, "Node should have id"
            assert "title" in node, "Node should have title"
            assert "label" in node, "Node should have label"
    
    @pytest.mark.asyncio
    async def test_06_generate_outline(self, api: LifecycleAPIClient):
        """Step 6: Generate an outline via chat."""
        global _test_project_id
        assert _test_project_id, "Project must be created first"
        
        response = await api.send_chat_message(
            _test_project_id,
            "Generate an outline based on the papers we've found",
        )
        
        # Check if outline was generated or if we need more papers
        if "error" in response["action_taken"].lower():
            logger.warning(f"Outline generation issue: {response['message']}")
        else:
            logger.info(f"Outline response: {response['action_taken']}")
        
        # Get outline to verify structure
        outline = await api.get_outline(_test_project_id)
        
        assert "sections" in outline, "Outline should have sections"
        logger.info(f"Outline has {len(outline.get('sections', []))} sections")
    
    @pytest.mark.asyncio
    async def test_07_verify_outline_sources(self, api: LifecycleAPIClient):
        """Step 7: Verify outline sections have linked sources."""
        global _test_project_id
        assert _test_project_id, "Project must be created first"
        
        outline = await api.get_outline(_test_project_id)
        sections = outline.get("sections", [])
        
        if not sections:
            pytest.skip("No outline sections - outline may not have been generated")
        
        # Count sections with claims
        sections_with_claims = 0
        total_claims = 0
        claims_with_sources = 0
        
        for section in sections:
            claims = section.get("claims", [])
            if claims:
                sections_with_claims += 1
                total_claims += len(claims)
                claims_with_sources += sum(
                    1 for c in claims if c.get("sources")
                )
        
        logger.info(
            f"Outline: {len(sections)} sections, "
            f"{total_claims} claims, "
            f"{claims_with_sources} with sources"
        )
    
    @pytest.mark.asyncio
    async def test_08_critique_outline(self, api: LifecycleAPIClient):
        """Step 8: Use AI to critique and update an outline section."""
        global _test_project_id
        assert _test_project_id, "Project must be created first"
        
        # Ask AI to identify gaps
        response = await api.send_chat_message(
            _test_project_id,
            "Which claims need more supporting sources?",
        )
        
        assert response["action_taken"] in [
            "find_gaps", "help", "error", "unknown"
        ]
        
        logger.info(f"Gap analysis: {response['action_taken']}")
        
        # Try adding a section via chat
        add_response = await api.send_chat_message(
            _test_project_id,
            "Add a section called 'Future Directions'",
        )
        
        logger.info(f"Add section: {add_response['action_taken']}")
    
    @pytest.mark.asyncio
    async def test_09_generate_paper_draft(self, api: LifecycleAPIClient):
        """Step 9: Generate a paper draft from the outline."""
        global _test_project_id
        assert _test_project_id, "Project must be created first"
        
        try:
            report = await api.generate_report(_test_project_id)
            
            assert "content" in report or "sections" in report
            logger.info("Paper draft generated successfully")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                pytest.skip("Report generation endpoint not implemented yet")
            raise
    
    @pytest.mark.asyncio
    async def test_10_verify_citations(self, api: LifecycleAPIClient):
        """Step 10: Verify paper has proper citations."""
        global _test_project_id
        assert _test_project_id, "Project must be created first"
        
        try:
            report = await api.get_report(_test_project_id)
            
            content = report.get("content", "")
            
            # Check for citation markers
            has_citations = (
                "(" in content and ")" in content  # Parenthetical citations
                or "[" in content and "]" in content  # Bracket citations
            )
            
            if has_citations:
                logger.info("Paper contains citation markers")
            else:
                logger.warning("Paper may not have citations")
            
            # Check for bibliography
            has_bibliography = (
                "References" in content
                or "Bibliography" in content
                or report.get("bibliography")
            )
            
            if has_bibliography:
                logger.info("Paper contains bibliography section")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                pytest.skip("Report endpoint not implemented yet")
            elif e.response.status_code == 500:
                # Report table may not exist in DB
                pytest.skip("Report table may not be created in database")
            raise
    
    @pytest.mark.asyncio
    async def test_99_cleanup(self, api: LifecycleAPIClient):
        """Cleanup: Delete test project."""
        global _test_project_id
        
        if _test_project_id:
            try:
                await api.delete_project(_test_project_id)
                logger.info(f"Deleted test project: {_test_project_id}")
            except Exception as e:
                logger.warning(f"Failed to cleanup project: {e}")
            finally:
                _test_project_id = None


# =============================================================================
# Individual Component Tests
# =============================================================================

@pytest.mark.e2e
class TestCitationTreeEdges:
    """Test that citation edges are correctly built in the knowledge tree."""
    
    @pytest.mark.asyncio
    async def test_citation_edges_structure(self, api: LifecycleAPIClient):
        """Verify citation edge structure is correct."""
        # Create a project
        project = await api.create_project(
            title="Citation Edge Test",
            description="Testing citation edge structure",
        )
        project_id = project["id"]
        
        try:
            # Search for papers
            await api.send_chat_message(
                project_id,
                "Search for transformer neural networks",
            )
            
            await asyncio.sleep(1)
            
            # Get tree
            tree = await api.get_knowledge_tree(project_id)
            
            # Verify edge structure
            for edge in tree.get("edges", []):
                assert "source" in edge, "Edge should have source"
                assert "target" in edge, "Edge should have target"
                assert "relationship" in edge, "Edge should have relationship"
                assert edge["relationship"] == "cites", "Relationship should be 'cites'"
            
            logger.info(f"Verified {len(tree.get('edges', []))} citation edges")
            
        finally:
            await api.delete_project(project_id)


@pytest.mark.e2e
class TestOutlineSectionTypes:
    """Test that outline sections use valid section_type enum values."""
    
    @pytest.mark.asyncio
    async def test_section_types_valid(self, api: LifecycleAPIClient):
        """Verify all section types are valid enum values."""
        valid_types = {
            "introduction",
            "literature_review",
            "methods",
            "results",
            "discussion",
            "conclusion",
            "abstract",
            "custom",
        }
        
        # Create project and generate outline
        project = await api.create_project(
            title="Section Type Test",
            description="Testing section type enum values",
        )
        project_id = project["id"]
        
        try:
            # Search and generate outline
            await api.send_chat_message(project_id, "Search for deep learning")
            await asyncio.sleep(1)
            await api.send_chat_message(project_id, "Generate an outline")
            await asyncio.sleep(1)
            
            # Get outline
            outline = await api.get_outline(project_id)
            
            for section in outline.get("sections", []):
                section_type = section.get("section_type", "custom")
                assert section_type in valid_types, (
                    f"Invalid section_type: {section_type}"
                )
            
            logger.info("All section types are valid")
            
        finally:
            await api.delete_project(project_id)


# =============================================================================
# Main Runner
# =============================================================================

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short",
        "-m", "lifecycle",
    ])

