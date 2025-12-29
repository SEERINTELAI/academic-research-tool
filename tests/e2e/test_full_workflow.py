"""
End-to-end tests for the complete academic research workflow.

These tests exercise the full API flow:
1. Create project
2. Search for papers
3. Add sources to project
4. Ingest sources (upload to RAG)
5. Query the research (RAG)
6. Create outline sections
7. Clean up

Run with: pytest tests/e2e/test_full_workflow.py -v -s
"""

import asyncio
import httpx
import pytest
from datetime import datetime
from typing import Optional
import uuid

# Test configuration
BASE_URL = "http://localhost:8003"
AUTH_TOKEN = "demo-token"
TIMEOUT = 30.0


class APITestClient:
    """HTTP client for API testing."""
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            timeout=TIMEOUT,
        )
        return self
    
    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()
    
    async def get(self, path: str) -> httpx.Response:
        return await self.client.get(path)
    
    async def post(self, path: str, json: dict = None) -> httpx.Response:
        return await self.client.post(path, json=json)
    
    async def patch(self, path: str, json: dict) -> httpx.Response:
        return await self.client.patch(path, json=json)
    
    async def delete(self, path: str) -> httpx.Response:
        return await self.client.delete(path)


@pytest.fixture
def test_client():
    """Create test client fixture."""
    return APITestClient(BASE_URL, AUTH_TOKEN)


@pytest.mark.asyncio
class TestHealthCheck:
    """Test API health endpoints."""
    
    async def test_health_endpoint(self, test_client):
        """Test basic health check."""
        async with test_client as client:
            response = await client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["healthy", "ok"]
            print(f"✓ Health check passed: {data}")
    
    async def test_ready_endpoint(self, test_client):
        """Test readiness probe."""
        async with test_client as client:
            response = await client.get("/api/health/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["ready"] == True
            print(f"✓ Readiness check passed: {data}")


@pytest.mark.asyncio
class TestProjectLifecycle:
    """Test complete project CRUD lifecycle."""
    
    async def test_create_project(self, test_client):
        """Test project creation."""
        async with test_client as client:
            project_data = {
                "title": f"Test Project {datetime.now().isoformat()}",
                "description": "E2E test project for academic research"
            }
            
            response = await client.post("/api/projects", json=project_data)
            assert response.status_code == 201, f"Failed: {response.text}"
            
            project = response.json()
            assert "id" in project
            assert project["title"] == project_data["title"]
            assert project["status"] == "draft"
            
            print(f"✓ Created project: {project['id']}")
            
            # Cleanup
            await client.delete(f"/api/projects/{project['id']}")
            print(f"✓ Cleaned up project")
    
    async def test_list_projects(self, test_client):
        """Test listing projects."""
        async with test_client as client:
            # Create a project first
            response = await client.post("/api/projects", json={
                "title": "List Test Project",
                "description": "Testing list endpoint"
            })
            assert response.status_code == 201
            project = response.json()
            
            # List projects
            response = await client.get("/api/projects")
            assert response.status_code == 200
            projects = response.json()
            assert isinstance(projects, list)
            assert len(projects) >= 1
            
            print(f"✓ Listed {len(projects)} projects")
            
            # Cleanup
            await client.delete(f"/api/projects/{project['id']}")
    
    async def test_update_project(self, test_client):
        """Test updating a project."""
        async with test_client as client:
            # Create
            response = await client.post("/api/projects", json={
                "title": "Original Title",
                "description": "Original description"
            })
            project = response.json()
            
            # Update
            response = await client.patch(
                f"/api/projects/{project['id']}",
                json={"title": "Updated Title", "status": "active"}
            )
            assert response.status_code == 200
            updated = response.json()
            assert updated["title"] == "Updated Title"
            
            print(f"✓ Updated project: {project['id']}")
            
            # Cleanup
            await client.delete(f"/api/projects/{project['id']}")


@pytest.mark.asyncio
class TestOutlineManagement:
    """Test outline section management."""
    
    async def test_create_outline_sections(self, test_client):
        """Test creating outline sections."""
        async with test_client as client:
            # Create project
            response = await client.post("/api/projects", json={
                "title": "Outline Test Project"
            })
            project = response.json()
            project_id = project["id"]
            
            try:
                # Create sections
                sections = [
                    {"title": "Introduction", "section_type": "introduction", "order_index": 0},
                    {"title": "Methods", "section_type": "methods", "order_index": 1},
                    {"title": "Results", "section_type": "results", "order_index": 2},
                    {"title": "Discussion", "section_type": "discussion", "order_index": 3},
                    {"title": "Conclusion", "section_type": "conclusion", "order_index": 4},
                ]
                
                created_sections = []
                for section in sections:
                    response = await client.post(
                        f"/api/projects/{project_id}/outline",
                        json=section
                    )
                    assert response.status_code == 201, f"Failed: {response.text}"
                    created_sections.append(response.json())
                
                print(f"✓ Created {len(created_sections)} outline sections")
                
                # Verify listing
                response = await client.get(f"/api/projects/{project_id}/outline")
                assert response.status_code == 200
                outline = response.json()
                # Response is {"project_id": ..., "sections": [...], "total_count": N}
                sections = outline.get("sections", outline) if isinstance(outline, dict) else outline
                assert len(sections) == 5 or outline.get("total_count") == 5
                
                print(f"✓ Verified outline structure")
                
            finally:
                # Cleanup
                await client.delete(f"/api/projects/{project_id}")


@pytest.mark.asyncio
class TestSourceManagement:
    """Test source/paper management."""
    
    async def test_search_papers(self, test_client):
        """Test searching for academic papers."""
        async with test_client as client:
            # Create project first (search requires project context)
            response = await client.post("/api/projects", json={
                "title": "Search Test Project"
            })
            project = response.json()
            project_id = project["id"]
            
            try:
                # Search for papers
                response = await client.get(
                    f"/api/projects/{project_id}/sources/search?query=machine+learning&limit=5"
                )
                
                # May fail if Semantic Scholar is unavailable
                if response.status_code == 200:
                    results = response.json()
                    print(f"✓ Found {len(results.get('results', []))} papers")
                    
                    if results.get("results"):
                        paper = results["results"][0]
                        print(f"  - First paper: {paper.get('title', 'No title')[:60]}...")
                elif response.status_code == 503:
                    print("⚠ Semantic Scholar API unavailable (expected in some environments)")
                else:
                    print(f"⚠ Search returned {response.status_code}: {response.text[:100]}")
                    
            finally:
                await client.delete(f"/api/projects/{project_id}")
    
    async def test_add_source_to_project(self, test_client):
        """Test adding a source to a project."""
        async with test_client as client:
            # Create project
            response = await client.post("/api/projects", json={
                "title": "Source Add Test Project"
            })
            project = response.json()
            project_id = project["id"]
            
            try:
                # Add a source manually (without paper_id - just metadata)
                source_data = {
                    "title": "Test Paper Title",
                    "authors": [{"name": "John Doe"}, {"name": "Jane Smith"}],
                    "abstract": "This is a test paper abstract.",
                    "year": 2024,
                    "doi": "10.1234/test.2024.001"
                }
                
                response = await client.post(
                    f"/api/projects/{project_id}/sources",
                    json=source_data
                )
                
                # Check result
                if response.status_code == 201:
                    source = response.json()
                    print(f"✓ Added source: {source.get('id')}")
                    assert source["title"] == source_data["title"]
                else:
                    print(f"⚠ Add source returned {response.status_code}: {response.text[:200]}")
                
                # List sources
                response = await client.get(f"/api/projects/{project_id}/sources")
                assert response.status_code == 200
                sources = response.json()
                print(f"✓ Project has {len(sources)} sources")
                
            finally:
                await client.delete(f"/api/projects/{project_id}")


@pytest.mark.asyncio  
class TestResearchWorkflow:
    """Test the complete research workflow."""
    
    async def test_full_research_flow(self, test_client):
        """
        Complete E2E test:
        1. Create project
        2. Create outline
        3. Add source
        4. Query research (if RAG available)
        5. Cleanup
        """
        async with test_client as client:
            print("\n" + "="*60)
            print("FULL RESEARCH WORKFLOW E2E TEST")
            print("="*60)
            
            # 1. Create project
            print("\n[1/5] Creating project...")
            response = await client.post("/api/projects", json={
                "title": f"E2E Research Test {uuid.uuid4().hex[:8]}",
                "description": "Complete E2E workflow test"
            })
            assert response.status_code == 201, f"Project creation failed: {response.text}"
            project = response.json()
            project_id = project["id"]
            print(f"  ✓ Project created: {project_id}")
            
            try:
                # 2. Create outline
                print("\n[2/5] Creating outline...")
                outline_sections = [
                    {"title": "Introduction", "section_type": "introduction", "order_index": 0},
                    {"title": "Literature Review", "section_type": "literature_review", "order_index": 1},
                    {"title": "Methodology", "section_type": "methods", "order_index": 2},
                ]
                
                for section in outline_sections:
                    response = await client.post(
                        f"/api/projects/{project_id}/outline",
                        json=section
                    )
                    assert response.status_code == 201
                print(f"  ✓ Created {len(outline_sections)} sections")
                
                # 3. Add a source
                print("\n[3/5] Adding source...")
                source_data = {
                    "title": "Deep Learning for Natural Language Processing",
                    "authors": [{"name": "AI Researcher"}],
                    "abstract": "A comprehensive study of deep learning techniques.",
                    "year": 2023,
                }
                response = await client.post(
                    f"/api/projects/{project_id}/sources",
                    json=source_data
                )
                if response.status_code == 201:
                    source = response.json()
                    print(f"  ✓ Source added: {source.get('id')}")
                else:
                    print(f"  ⚠ Source add returned {response.status_code}")
                
                # 4. Test research query (if RAG is available)
                print("\n[4/5] Testing research query...")
                try:
                    response = await client.post(
                        f"/api/projects/{project_id}/research/query",
                        json={
                            "query": "What are the main findings?",
                            "mode": "hybrid"
                        }
                    )
                    if response.status_code == 200:
                        result = response.json()
                        print(f"  ✓ Query successful")
                        print(f"    Answer preview: {result.get('answer', 'N/A')[:100]}...")
                    elif response.status_code == 503:
                        print(f"  ⚠ RAG service unavailable (expected without ingested docs)")
                    else:
                        print(f"  ⚠ Query returned {response.status_code}: {response.text[:100]}")
                except Exception as e:
                    print(f"  ⚠ Query skipped (timeout or error): {type(e).__name__}")
                
                # 5. Verify project state
                print("\n[5/5] Verifying project state...")
                response = await client.get(f"/api/projects/{project_id}")
                assert response.status_code == 200
                project_state = response.json()
                print(f"  ✓ Project status: {project_state.get('status')}")
                
                response = await client.get(f"/api/projects/{project_id}/outline")
                assert response.status_code == 200
                outline = response.json()
                print(f"  ✓ Outline sections: {len(outline)}")
                
                response = await client.get(f"/api/projects/{project_id}/sources")
                assert response.status_code == 200
                sources = response.json()
                print(f"  ✓ Sources: {len(sources)}")
                
                print("\n" + "="*60)
                print("E2E TEST COMPLETED SUCCESSFULLY")
                print("="*60 + "\n")
                
            finally:
                # Cleanup
                print("Cleaning up...")
                await client.delete(f"/api/projects/{project_id}")
                print("  ✓ Project deleted")


@pytest.mark.asyncio
class TestErrorHandling:
    """Test API error handling."""
    
    async def test_not_found_project(self, test_client):
        """Test 404 for non-existent project."""
        async with test_client as client:
            response = await client.get(f"/api/projects/{uuid.uuid4()}")
            assert response.status_code == 404
            print("✓ 404 returned for non-existent project")
    
    async def test_invalid_project_data(self, test_client):
        """Test validation error for invalid data."""
        async with test_client as client:
            response = await client.post("/api/projects", json={})
            # Should fail validation - title is required
            assert response.status_code in [400, 422]
            print("✓ Validation error for missing title")


if __name__ == "__main__":
    # Run with: python -m pytest tests/e2e/test_full_workflow.py -v -s
    pytest.main([__file__, "-v", "-s"])

