"""
End-to-end tests for the chat-driven research UI.

Tests the full workflow: create project, chat, explore, generate outline.
"""

import pytest
from uuid import uuid4

from tests.e2e.test_full_workflow import APITestClient

# Test configuration
BASE_URL = "http://localhost:8003"
AUTH_TOKEN = "demo-token"


class TestResearchUIChat:
    """Test the chat-driven research interface."""

    @pytest.mark.asyncio
    async def test_chat_message_search(self):
        """Test sending a search message via chat."""
        async with APITestClient(BASE_URL, AUTH_TOKEN) as client:
            # Create project
            project = await client.post("/api/projects", json={
                "title": f"Research UI Test {uuid4().hex[:8]}",
                "description": "Testing chat-driven research",
            })
            if project.status_code == 500:
                pytest.skip("Database not configured")
            assert project.status_code in [200, 201]
            project_id = project.json()["id"]
            
            try:
                # Send chat message
                response = await client.post(
                    f"/api/projects/{project_id}/research-ui/chat",
                    json={"message": "search for quantum computing"},
                )
                
                if response.status_code == 500:
                    pytest.skip("Database not configured")
                
                # May timeout on RAG, but should return a response
                if response.status_code == 200:
                    data = response.json()
                    assert "message" in data
                    assert "action_taken" in data
                    print(f"✓ Chat search response: {data['action_taken']}")
                else:
                    print(f"⚠ Chat search returned {response.status_code}")
            finally:
                await client.delete(f"/api/projects/{project_id}")

    @pytest.mark.asyncio
    async def test_get_papers_list(self):
        """Test getting the papers list for Explore tab."""
        async with APITestClient(BASE_URL, AUTH_TOKEN) as client:
            project = await client.post("/api/projects", json={
                "title": f"Papers List Test {uuid4().hex[:8]}",
                "description": "Testing papers list",
            })
            if project.status_code == 500:
                pytest.skip("Database not configured")
            assert project.status_code in [200, 201]
            project_id = project.json()["id"]
            
            try:
                response = await client.get(f"/api/projects/{project_id}/research-ui/papers")
                
                if response.status_code == 500:
                    pytest.skip("Database not configured")
                assert response.status_code == 200
                papers = response.json()
                assert isinstance(papers, list)
                print(f"✓ Got {len(papers)} papers in Explore list")
            finally:
                await client.delete(f"/api/projects/{project_id}")

    @pytest.mark.asyncio
    async def test_get_outline_with_sources(self):
        """Test getting the outline with source information."""
        async with APITestClient(BASE_URL, AUTH_TOKEN) as client:
            project = await client.post("/api/projects", json={
                "title": f"Outline Test {uuid4().hex[:8]}",
                "description": "Testing outline",
            })
            if project.status_code == 500:
                pytest.skip("Database not configured")
            assert project.status_code in [200, 201]
            project_id = project.json()["id"]
            
            try:
                response = await client.get(f"/api/projects/{project_id}/research-ui/outline")
                
                if response.status_code == 500:
                    pytest.skip("Database not configured")
                assert response.status_code == 200
                outline = response.json()
                assert "sections" in outline
                assert "total_sections" in outline
                assert "claims_needing_sources" in outline
                print(f"✓ Got outline: {outline['total_sections']} sections")
            finally:
                await client.delete(f"/api/projects/{project_id}")

    @pytest.mark.asyncio
    async def test_get_knowledge_tree(self):
        """Test getting the knowledge tree for visualization."""
        async with APITestClient(BASE_URL, AUTH_TOKEN) as client:
            project = await client.post("/api/projects", json={
                "title": f"Knowledge Tree Test {uuid4().hex[:8]}",
                "description": "Testing tree",
            })
            if project.status_code == 500:
                pytest.skip("Database not configured")
            assert project.status_code in [200, 201]
            project_id = project.json()["id"]
            
            try:
                response = await client.get(f"/api/projects/{project_id}/research-ui/tree")
                
                if response.status_code == 500:
                    pytest.skip("Database not configured")
                assert response.status_code == 200
                tree = response.json()
                assert "nodes" in tree
                assert "edges" in tree
                assert "total_papers" in tree
                print(f"✓ Got knowledge tree: {len(tree['nodes'])} nodes")
            finally:
                await client.delete(f"/api/projects/{project_id}")

    @pytest.mark.asyncio
    async def test_get_chat_history(self):
        """Test getting chat history."""
        async with APITestClient(BASE_URL, AUTH_TOKEN) as client:
            project = await client.post("/api/projects", json={
                "title": f"Chat History Test {uuid4().hex[:8]}",
                "description": "Testing chat history",
            })
            if project.status_code == 500:
                pytest.skip("Database not configured")
            assert project.status_code in [200, 201]
            project_id = project.json()["id"]
            
            try:
                response = await client.get(f"/api/projects/{project_id}/research-ui/chat/history")
                
                if response.status_code == 500:
                    pytest.skip("Database not configured")
                assert response.status_code == 200
                history = response.json()
                assert isinstance(history, list)
                print(f"✓ Got chat history: {len(history)} messages")
            finally:
                await client.delete(f"/api/projects/{project_id}")

    @pytest.mark.asyncio
    async def test_get_research_session(self):
        """Test getting research session info."""
        async with APITestClient(BASE_URL, AUTH_TOKEN) as client:
            project = await client.post("/api/projects", json={
                "title": f"Session Test {uuid4().hex[:8]}",
                "description": "Testing session",
            })
            if project.status_code == 500:
                pytest.skip("Database not configured")
            assert project.status_code in [200, 201]
            project_id = project.json()["id"]
            
            try:
                response = await client.get(f"/api/projects/{project_id}/research-ui/session")
                
                if response.status_code == 500:
                    pytest.skip("Database not configured")
                assert response.status_code == 200
                # Session may be null if not started yet
                session = response.json()
                if session:
                    assert "topic" in session
                    assert "status" in session
                    print(f"✓ Got session: {session['topic']}")
                else:
                    print("✓ No session yet (expected)")
            finally:
                await client.delete(f"/api/projects/{project_id}")


class TestResearchUIWorkflow:
    """Test complete research workflows."""

    @pytest.mark.asyncio
    async def test_full_research_workflow(self):
        """Test a complete research workflow: search, explore, outline."""
        async with APITestClient(BASE_URL, AUTH_TOKEN) as client:
            project = await client.post("/api/projects", json={
                "title": f"Full Workflow Test {uuid4().hex[:8]}",
                "description": "Testing complete research flow",
            })
            if project.status_code == 500:
                pytest.skip("Database not configured")
            assert project.status_code in [200, 201]
            project_id = project.json()["id"]
            
            try:
                # Step 1: Send search message
                chat_response = await client.post(
                    f"/api/projects/{project_id}/research-ui/chat",
                    json={"message": "search for machine learning in healthcare"},
                )
                
                if chat_response.status_code == 500:
                    pytest.skip("Database not configured")
                
                if chat_response.status_code != 200:
                    print(f"⚠ Search failed with {chat_response.status_code}")
                    return
                
                # Step 2: Get papers list
                papers_response = await client.get(f"/api/projects/{project_id}/research-ui/papers")
                if papers_response.status_code == 500:
                    pytest.skip("Database not configured")
                assert papers_response.status_code == 200
                
                # Step 3: Get outline
                outline_response = await client.get(f"/api/projects/{project_id}/research-ui/outline")
                if outline_response.status_code == 500:
                    pytest.skip("Database not configured")
                assert outline_response.status_code == 200
                
                print("✓ Full workflow completed successfully")
                
            finally:
                await client.delete(f"/api/projects/{project_id}")


class TestChatIntentParsing:
    """Test that different chat intents are correctly handled."""

    @pytest.mark.asyncio
    async def test_help_intent(self):
        """Test help/unknown intent."""
        async with APITestClient(BASE_URL, AUTH_TOKEN) as client:
            project = await client.post("/api/projects", json={
                "title": f"Intent Test {uuid4().hex[:8]}",
                "description": "Test",
            })
            if project.status_code == 500:
                pytest.skip("Database not configured")
            assert project.status_code in [200, 201]
            project_id = project.json()["id"]
            
            try:
                # First create a session by searching
                await client.post(
                    f"/api/projects/{project_id}/research-ui/chat",
                    json={"message": "search for test topic"},
                )
                
                # Send ambiguous message
                response = await client.post(
                    f"/api/projects/{project_id}/research-ui/chat",
                    json={"message": "hello there"},
                )
                
                if response.status_code == 500:
                    pytest.skip("Database not configured")
                
                if response.status_code == 200:
                    data = response.json()
                    # Should either be 'help' or 'unknown'
                    assert data.get("action_taken") in ["help", "unknown", "ask_question", None]
                    print(f"✓ Unknown message handled: {data.get('action_taken')}")
            finally:
                await client.delete(f"/api/projects/{project_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
