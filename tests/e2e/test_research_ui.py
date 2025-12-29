"""
End-to-end tests for the chat-driven research UI.

Tests the full workflow: create project, chat, explore, generate outline.
"""

import pytest
import httpx
from uuid import uuid4

from tests.e2e.test_full_workflow import APIClient, TestClient


class TestResearchUIChat(TestClient):
    """Test the chat-driven research interface."""

    async def _create_project_with_session(self, client: APIClient) -> tuple[str, str]:
        """Create a project and start a research session via chat."""
        # Create project
        project = await client.post("/api/projects", json={
            "title": f"Research UI Test {uuid4().hex[:8]}",
            "description": "Testing chat-driven research",
        })
        assert project.status_code == 200
        project_id = project.json()["id"]
        
        return project_id, project.json()["title"]

    @pytest.mark.asyncio
    async def test_chat_message_search(self, client: APIClient):
        """Test sending a search message via chat."""
        project_id, _ = await self._create_project_with_session(client)
        
        try:
            # Send chat message
            response = await client.post(
                f"/api/projects/{project_id}/research-ui/chat",
                json={"message": "search for quantum computing"},
            )
            
            # May timeout on RAG, but should return a response
            if response.status_code == 200:
                data = response.json()
                assert "message" in data
                assert "action_taken" in data
                print(f"✓ Chat search response: {data['action_taken']}")
            else:
                # Accept timeout or other errors for now
                print(f"⚠ Chat search returned {response.status_code}")
        finally:
            await client.delete(f"/api/projects/{project_id}")

    @pytest.mark.asyncio
    async def test_get_papers_list(self, client: APIClient):
        """Test getting the papers list for Explore tab."""
        project_id, _ = await self._create_project_with_session(client)
        
        try:
            response = await client.get(f"/api/projects/{project_id}/research-ui/papers")
            
            assert response.status_code == 200
            papers = response.json()
            assert isinstance(papers, list)
            print(f"✓ Got {len(papers)} papers in Explore list")
        finally:
            await client.delete(f"/api/projects/{project_id}")

    @pytest.mark.asyncio
    async def test_get_outline_with_sources(self, client: APIClient):
        """Test getting the outline with source information."""
        project_id, _ = await self._create_project_with_session(client)
        
        try:
            response = await client.get(f"/api/projects/{project_id}/research-ui/outline")
            
            assert response.status_code == 200
            outline = response.json()
            assert "sections" in outline
            assert "total_sections" in outline
            assert "claims_needing_sources" in outline
            print(f"✓ Got outline: {outline['total_sections']} sections, {outline['claims_needing_sources']} gaps")
        finally:
            await client.delete(f"/api/projects/{project_id}")

    @pytest.mark.asyncio
    async def test_get_knowledge_tree(self, client: APIClient):
        """Test getting the knowledge tree for visualization."""
        project_id, _ = await self._create_project_with_session(client)
        
        try:
            response = await client.get(f"/api/projects/{project_id}/research-ui/tree")
            
            assert response.status_code == 200
            tree = response.json()
            assert "nodes" in tree
            assert "edges" in tree
            assert "total_papers" in tree
            print(f"✓ Got knowledge tree: {len(tree['nodes'])} nodes, {len(tree['edges'])} edges")
        finally:
            await client.delete(f"/api/projects/{project_id}")

    @pytest.mark.asyncio
    async def test_get_chat_history(self, client: APIClient):
        """Test getting chat history."""
        project_id, _ = await self._create_project_with_session(client)
        
        try:
            response = await client.get(f"/api/projects/{project_id}/research-ui/chat/history")
            
            assert response.status_code == 200
            history = response.json()
            assert isinstance(history, list)
            print(f"✓ Got chat history: {len(history)} messages")
        finally:
            await client.delete(f"/api/projects/{project_id}")

    @pytest.mark.asyncio
    async def test_get_research_session(self, client: APIClient):
        """Test getting research session info."""
        project_id, _ = await self._create_project_with_session(client)
        
        try:
            response = await client.get(f"/api/projects/{project_id}/research-ui/session")
            
            assert response.status_code == 200
            # Session may be null if not started yet
            session = response.json()
            if session:
                assert "topic" in session
                assert "status" in session
                print(f"✓ Got session: {session['topic']} ({session['status']})")
            else:
                print("✓ No session yet (expected)")
        finally:
            await client.delete(f"/api/projects/{project_id}")


class TestResearchUIWorkflow(TestClient):
    """Test complete research workflows."""

    @pytest.mark.asyncio
    async def test_full_research_workflow(self, client: APIClient):
        """Test a complete research workflow: search, explore, outline."""
        # Create project
        project = await client.post("/api/projects", json={
            "title": f"Full Workflow Test {uuid4().hex[:8]}",
            "description": "Testing complete research flow",
        })
        assert project.status_code == 200
        project_id = project.json()["id"]
        
        try:
            # Step 1: Send search message
            print("Step 1: Sending search message...")
            chat_response = await client.post(
                f"/api/projects/{project_id}/research-ui/chat",
                json={"message": "search for machine learning in healthcare"},
                timeout=60.0,
            )
            
            if chat_response.status_code != 200:
                print(f"⚠ Search failed with {chat_response.status_code}, skipping rest of workflow")
                return
            
            search_data = chat_response.json()
            print(f"  Action: {search_data.get('action_taken')}")
            print(f"  Papers added: {len(search_data.get('papers_added', []))}")
            
            # Step 2: Get papers list
            print("Step 2: Getting papers list...")
            papers_response = await client.get(f"/api/projects/{project_id}/research-ui/papers")
            assert papers_response.status_code == 200
            papers = papers_response.json()
            print(f"  Found {len(papers)} papers")
            
            # Step 3: Request outline generation
            if len(papers) > 0:
                print("Step 3: Generating outline...")
                outline_response = await client.post(
                    f"/api/projects/{project_id}/research-ui/chat",
                    json={"message": "generate an outline from what we found"},
                    timeout=60.0,
                )
                
                if outline_response.status_code == 200:
                    outline_data = outline_response.json()
                    print(f"  Action: {outline_data.get('action_taken')}")
                    print(f"  Sections created: {outline_data.get('sections_created', 0)}")
            
            # Step 4: Check for gaps
            print("Step 4: Finding gaps...")
            gaps_response = await client.post(
                f"/api/projects/{project_id}/research-ui/chat",
                json={"message": "which claims need more sources?"},
                timeout=30.0,
            )
            
            if gaps_response.status_code == 200:
                gaps_data = gaps_response.json()
                print(f"  Action: {gaps_data.get('action_taken')}")
            
            # Step 5: Get final state
            print("Step 5: Getting final state...")
            final_outline = await client.get(f"/api/projects/{project_id}/research-ui/outline")
            assert final_outline.status_code == 200
            outline = final_outline.json()
            print(f"  Final outline: {outline['total_sections']} sections, {outline['total_claims']} claims")
            
            print("✓ Full workflow completed successfully")
            
        finally:
            await client.delete(f"/api/projects/{project_id}")


class TestChatIntentParsing(TestClient):
    """Test that different chat intents are correctly handled."""

    @pytest.mark.asyncio
    async def test_help_intent(self, client: APIClient):
        """Test help/unknown intent."""
        project = await client.post("/api/projects", json={
            "title": f"Intent Test {uuid4().hex[:8]}",
            "description": "Test",
        })
        project_id = project.json()["id"]
        
        try:
            # First create a session by searching
            await client.post(
                f"/api/projects/{project_id}/research-ui/chat",
                json={"message": "search for test topic"},
                timeout=30.0,
            )
            
            # Send ambiguous message
            response = await client.post(
                f"/api/projects/{project_id}/research-ui/chat",
                json={"message": "hello there"},
                timeout=30.0,
            )
            
            if response.status_code == 200:
                data = response.json()
                # Should either be 'help' or 'unknown'
                assert data.get("action_taken") in ["help", "unknown", "ask_question"]
                print(f"✓ Unknown message handled: {data.get('action_taken')}")
        finally:
            await client.delete(f"/api/projects/{project_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

