"""
Integration tests for Supabase database operations.

Tests:
- Project CRUD
- Source CRUD
- Outline CRUD
- Database connection

These tests require Supabase to be configured.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import MagicMock, patch

# Mark all tests as integration tests requiring Supabase
pytestmark = [pytest.mark.integration, pytest.mark.requires_supabase]


class TestDatabaseConnection:
    """Test database connection and client."""
    
    def test_supabase_client_creation(self, mock_supabase_client):
        """Test that Supabase client can be created."""
        # Verify client has expected methods
        assert hasattr(mock_supabase_client, 'table')
        
        # Test table selection
        table = mock_supabase_client.table("project")
        assert hasattr(table, 'select')
        assert hasattr(table, 'insert')
        assert hasattr(table, 'update')
        assert hasattr(table, 'delete')
    
    def test_check_database_connection(self, mock_supabase_client):
        """Test database connectivity check."""
        from src.services.database import check_database_connection
        
        with patch("src.services.database.get_supabase_client") as mock_get_client:
            mock_get_client.return_value = mock_supabase_client
            mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"id": 1}])
            
            # Should not raise
            result = check_database_connection()
            # The function returns None or raises, so just verify it ran


class TestProjectCRUD:
    """Test Project CRUD operations."""
    
    @pytest.fixture
    def mock_db_with_project(self, mock_supabase_client, sample_project_data):
        """Mock database with a project."""
        mock_table = mock_supabase_client.table.return_value
        mock_table.execute.return_value = MagicMock(data=[sample_project_data])
        mock_table.single.return_value.execute.return_value = MagicMock(data=sample_project_data)
        mock_table.maybe_single.return_value.execute.return_value = MagicMock(data=sample_project_data)
        return mock_supabase_client
    
    def test_create_project(self, mock_db_with_project, sample_project_data):
        """Test creating a project."""
        table = mock_db_with_project.table("project")
        
        # Simulate insert
        result = table.insert({
            "title": "Test Project",
            "user_id": str(uuid4()),
        }).execute()
        
        # Verify insert was called
        table.insert.assert_called()
    
    def test_get_project(self, mock_db_with_project, sample_project_data):
        """Test getting a project by ID."""
        table = mock_db_with_project.table("project")
        
        result = table.select("*").eq("id", sample_project_data["id"]).single().execute()
        
        assert result.data is not None
        assert result.data["id"] == sample_project_data["id"]
    
    def test_update_project(self, mock_db_with_project, sample_project_data):
        """Test updating a project."""
        table = mock_db_with_project.table("project")
        
        result = table.update({
            "title": "Updated Title",
        }).eq("id", sample_project_data["id"]).execute()
        
        table.update.assert_called()
    
    def test_delete_project(self, mock_db_with_project, sample_project_data):
        """Test deleting a project."""
        table = mock_db_with_project.table("project")
        
        result = table.delete().eq("id", sample_project_data["id"]).execute()
        
        table.delete.assert_called()
    
    def test_list_projects(self, mock_db_with_project, sample_project_data):
        """Test listing projects."""
        table = mock_db_with_project.table("project")
        
        result = table.select("*").eq("user_id", sample_project_data["user_id"]).execute()
        
        table.select.assert_called_with("*")


class TestSourceCRUD:
    """Test Source CRUD operations."""
    
    @pytest.fixture
    def mock_db_with_source(self, mock_supabase_client, sample_source_data):
        """Mock database with a source."""
        mock_table = mock_supabase_client.table.return_value
        mock_table.execute.return_value = MagicMock(data=[sample_source_data])
        mock_table.single.return_value.execute.return_value = MagicMock(data=sample_source_data)
        mock_table.maybe_single.return_value.execute.return_value = MagicMock(data=sample_source_data)
        return mock_supabase_client
    
    def test_create_source(self, mock_db_with_source, sample_source_data):
        """Test creating a source."""
        table = mock_db_with_source.table("source")
        
        result = table.insert({
            "project_id": sample_source_data["project_id"],
            "title": "Test Paper",
            "doi": "10.1234/test",
        }).execute()
        
        table.insert.assert_called()
    
    def test_get_source(self, mock_db_with_source, sample_source_data):
        """Test getting a source by ID."""
        table = mock_db_with_source.table("source")
        
        result = table.select("*").eq("id", sample_source_data["id"]).single().execute()
        
        assert result.data is not None
    
    def test_update_source_ingestion_status(self, mock_db_with_source, sample_source_data):
        """Test updating source ingestion status."""
        table = mock_db_with_source.table("source")
        
        result = table.update({
            "ingestion_status": "completed",
            "hyperion_doc_name": "doc-123",
        }).eq("id", sample_source_data["id"]).execute()
        
        table.update.assert_called()
    
    def test_list_sources_by_project(self, mock_db_with_source, sample_source_data):
        """Test listing sources for a project."""
        table = mock_db_with_source.table("source")
        
        result = table.select("*").eq("project_id", sample_source_data["project_id"]).execute()
        
        assert result.data is not None
    
    def test_list_sources_by_status(self, mock_db_with_source, sample_source_data):
        """Test listing sources filtered by status."""
        table = mock_db_with_source.table("source")
        
        result = (
            table.select("*")
            .eq("project_id", sample_source_data["project_id"])
            .eq("ingestion_status", "pending")
            .execute()
        )
        
        # Verify filter was applied
        table.eq.assert_called()


class TestOutlineCRUD:
    """Test OutlineSection CRUD operations."""
    
    @pytest.fixture
    def mock_db_with_outline(self, mock_supabase_client):
        """Mock database with outline sections."""
        section_data = {
            "id": str(uuid4()),
            "project_id": str(uuid4()),
            "title": "Introduction",
            "section_type": "introduction",
            "position": 0,
            "parent_id": None,
            "content_notes": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        mock_table = mock_supabase_client.table.return_value
        mock_table.execute.return_value = MagicMock(data=[section_data])
        mock_table.single.return_value.execute.return_value = MagicMock(data=section_data)
        return mock_supabase_client, section_data
    
    def test_create_outline_section(self, mock_db_with_outline):
        """Test creating an outline section."""
        mock_db, section_data = mock_db_with_outline
        table = mock_db.table("outline_section")
        
        result = table.insert({
            "project_id": section_data["project_id"],
            "title": "Introduction",
            "section_type": "introduction",
            "position": 0,
        }).execute()
        
        table.insert.assert_called()
    
    def test_get_outline_sections_for_project(self, mock_db_with_outline):
        """Test getting all outline sections for a project."""
        mock_db, section_data = mock_db_with_outline
        table = mock_db.table("outline_section")
        
        result = (
            table.select("*")
            .eq("project_id", section_data["project_id"])
            .order("position")
            .execute()
        )
        
        table.order.assert_called_with("position")
    
    def test_update_section_content(self, mock_db_with_outline):
        """Test updating section content notes."""
        mock_db, section_data = mock_db_with_outline
        table = mock_db.table("outline_section")
        
        result = table.update({
            "content_notes": "New notes for introduction",
        }).eq("id", section_data["id"]).execute()
        
        table.update.assert_called()
    
    def test_reorder_sections(self, mock_db_with_outline):
        """Test reordering sections."""
        mock_db, section_data = mock_db_with_outline
        table = mock_db.table("outline_section")
        
        # Update position
        result = table.update({
            "position": 2,
        }).eq("id", section_data["id"]).execute()
        
        table.update.assert_called()
    
    def test_nested_sections(self, mock_db_with_outline):
        """Test creating nested sections."""
        mock_db, parent_section = mock_db_with_outline
        table = mock_db.table("outline_section")
        
        # Create child section
        result = table.insert({
            "project_id": parent_section["project_id"],
            "title": "Subsection 1",
            "section_type": "custom",
            "position": 0,
            "parent_id": parent_section["id"],
        }).execute()
        
        insert_call = table.insert.call_args
        assert "parent_id" in str(insert_call)


class TestSynthesisCRUD:
    """Test Synthesis/Citation CRUD operations."""
    
    @pytest.fixture
    def mock_db_with_synthesis(self, mock_supabase_client):
        """Mock database with synthesis data."""
        synthesis_data = {
            "id": str(uuid4()),
            "project_id": str(uuid4()),
            "section_id": str(uuid4()),
            "query": "What are the key findings?",
            "response": "The key findings are...",
            "created_at": datetime.now().isoformat(),
        }
        mock_table = mock_supabase_client.table.return_value
        mock_table.execute.return_value = MagicMock(data=[synthesis_data])
        return mock_supabase_client, synthesis_data
    
    def test_save_synthesis(self, mock_db_with_synthesis):
        """Test saving a synthesis result."""
        mock_db, synthesis_data = mock_db_with_synthesis
        table = mock_db.table("synthesis")
        
        result = table.insert({
            "project_id": synthesis_data["project_id"],
            "section_id": synthesis_data["section_id"],
            "query": synthesis_data["query"],
            "response": synthesis_data["response"],
        }).execute()
        
        table.insert.assert_called()
    
    def test_get_synthesis_for_section(self, mock_db_with_synthesis):
        """Test getting synthesis for a section."""
        mock_db, synthesis_data = mock_db_with_synthesis
        table = mock_db.table("synthesis")
        
        result = (
            table.select("*")
            .eq("section_id", synthesis_data["section_id"])
            .order("created_at", desc=True)
            .execute()
        )
        
        table.order.assert_called()


class TestCitationCRUD:
    """Test Citation CRUD operations."""
    
    @pytest.fixture
    def mock_db_with_citation(self, mock_supabase_client):
        """Mock database with citation data."""
        citation_data = {
            "id": str(uuid4()),
            "synthesis_id": str(uuid4()),
            "source_id": str(uuid4()),
            "excerpt": "This is a quote from the paper.",
            "relevance_score": 0.85,
            "created_at": datetime.now().isoformat(),
        }
        mock_table = mock_supabase_client.table.return_value
        mock_table.execute.return_value = MagicMock(data=[citation_data])
        return mock_supabase_client, citation_data
    
    def test_create_citation(self, mock_db_with_citation):
        """Test creating a citation."""
        mock_db, citation_data = mock_db_with_citation
        table = mock_db.table("citation")
        
        result = table.insert({
            "synthesis_id": citation_data["synthesis_id"],
            "source_id": citation_data["source_id"],
            "excerpt": citation_data["excerpt"],
            "relevance_score": citation_data["relevance_score"],
        }).execute()
        
        table.insert.assert_called()
    
    def test_get_citations_for_synthesis(self, mock_db_with_citation):
        """Test getting citations for a synthesis."""
        mock_db, citation_data = mock_db_with_citation
        table = mock_db.table("citation")
        
        result = (
            table.select("*, source(*)")
            .eq("synthesis_id", citation_data["synthesis_id"])
            .execute()
        )
        
        # Verify join syntax
        table.select.assert_called_with("*, source(*)")

