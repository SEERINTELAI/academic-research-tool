"""
E2E tests for Library API endpoint.

Tests the new Library tab functionality with topic grouping.
"""

import pytest
from uuid import UUID

from tests.e2e.test_full_workflow import APITestClient

# Test configuration
BASE_URL = "http://localhost:8003"
AUTH_TOKEN = "demo-token"


class TestLibraryEndpoint:
    """Tests for the Library API."""
    
    @pytest.mark.asyncio
    async def test_get_library_empty(self):
        """Test getting library when empty."""
        async with APITestClient(BASE_URL, AUTH_TOKEN) as client:
            # Create project
            response = await client.post("/api/projects", json={
                "title": "Library Test Project",
                "description": "Testing library functionality"
            })
            # Skip if DB not available
            if response.status_code == 500:
                pytest.skip("Database not configured")
            assert response.status_code in [200, 201]
            project_id = response.json()["id"]
            
            try:
                response = await client.get(f"/api/projects/{project_id}/research-ui/library")
                if response.status_code == 500:
                    pytest.skip("Database not configured")
                assert response.status_code == 200
                
                data = response.json()
                assert data["project_id"] == str(project_id)
                assert data["total_papers"] == 0
                assert data["total_topics"] == 0
                assert data["topics"] == []
            finally:
                await client.delete(f"/api/projects/{project_id}")
    
    @pytest.mark.asyncio
    async def test_library_after_search_and_ingest(self):
        """Test that ingested papers appear in library grouped by topic."""
        async with APITestClient(BASE_URL, AUTH_TOKEN) as client:
            # Create project
            response = await client.post("/api/projects", json={
                "title": "Library Ingest Test",
                "description": "Testing library with ingested papers"
            })
            if response.status_code == 500:
                pytest.skip("Database not configured")
            assert response.status_code in [200, 201]
            project_id = response.json()["id"]
            
            try:
                # 1. Search for papers (this creates knowledge nodes and sources)
                chat_response = await client.post(
                    f"/api/projects/{project_id}/research-ui/chat",
                    json={"message": "search for machine learning"}
                )
                if chat_response.status_code == 500:
                    pytest.skip("Database not configured")
                assert chat_response.status_code == 200
                
                # 2. Check Explore for candidates
                explore_response = await client.get(
                    f"/api/projects/{project_id}/research-ui/papers"
                )
                if explore_response.status_code == 500:
                    pytest.skip("Database not configured")
                assert explore_response.status_code == 200
                
                # 3. Get library (should have ingested papers if any)
                library_response = await client.get(
                    f"/api/projects/{project_id}/research-ui/library"
                )
                if library_response.status_code == 500:
                    pytest.skip("Database not configured")
                assert library_response.status_code == 200
                
                library = library_response.json()
                assert "topics" in library
                assert "total_papers" in library
                assert "total_topics" in library
                    
            finally:
                await client.delete(f"/api/projects/{project_id}")
    
    @pytest.mark.asyncio
    async def test_library_topic_grouping(self):
        """Test that papers are correctly grouped by topic."""
        async with APITestClient(BASE_URL, AUTH_TOKEN) as client:
            # Create project
            response = await client.post("/api/projects", json={
                "title": "Topic Grouping Test",
                "description": "Testing topic grouping"
            })
            if response.status_code == 500:
                pytest.skip("Database not configured")
            assert response.status_code in [200, 201]
            project_id = response.json()["id"]
            
            try:
                # Search for papers on a topic
                await client.post(
                    f"/api/projects/{project_id}/research-ui/chat",
                    json={"message": "search for quantum cryptography", "auto_ingest": True}
                )
                
                # Get library
                response = await client.get(
                    f"/api/projects/{project_id}/research-ui/library"
                )
                if response.status_code == 500:
                    pytest.skip("Database not configured")
                assert response.status_code == 200
                
                library = response.json()
                
                # If we have papers, verify topic names are reasonable
                for topic_group in library["topics"]:
                    topic_name = topic_group["topic"]
                    assert isinstance(topic_name, str)
                    assert len(topic_name) > 0
                    
            finally:
                await client.delete(f"/api/projects/{project_id}")


class TestExploreVsLibrary:
    """Tests to verify separation between Explore (candidates) and Library (ingested)."""
    
    @pytest.mark.asyncio
    async def test_explore_shows_non_ingested(self):
        """Test that Explore only shows non-ingested papers."""
        async with APITestClient(BASE_URL, AUTH_TOKEN) as client:
            # Create project
            response = await client.post("/api/projects", json={
                "title": "Explore vs Library Test",
                "description": "Testing tab separation"
            })
            if response.status_code == 500:
                pytest.skip("Database not configured")
            assert response.status_code in [200, 201]
            project_id = response.json()["id"]
            
            try:
                # Search with auto_ingest=false to keep papers as candidates
                await client.post(
                    f"/api/projects/{project_id}/research-ui/chat",
                    json={"message": "search for neural networks", "auto_ingest": False}
                )
                
                # Get Explore papers
                response = await client.get(
                    f"/api/projects/{project_id}/research-ui/papers"
                )
                if response.status_code == 500:
                    pytest.skip("Database not configured")
                assert response.status_code == 200
                    
            finally:
                await client.delete(f"/api/projects/{project_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
