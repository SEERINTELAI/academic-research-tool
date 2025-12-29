"""
Unit tests for Pydantic models.

Tests:
- Model validation
- Enum values
- Optional field handling
- Default values
"""

import pytest
from datetime import datetime
from uuid import uuid4

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestProjectModels:
    """Test Project-related models."""
    
    def test_project_create_minimal(self):
        """Test ProjectCreate with minimal data."""
        from src.models.project import ProjectCreate
        
        project = ProjectCreate(title="Test Project")
        
        assert project.title == "Test Project"
        assert project.description is None
    
    def test_project_create_full(self):
        """Test ProjectCreate with all fields."""
        from src.models.project import ProjectCreate
        
        project = ProjectCreate(
            title="Research Paper",
            description="A detailed study on transformers",
        )
        
        assert project.title == "Research Paper"
        assert project.description == "A detailed study on transformers"
    
    def test_project_status_enum(self):
        """Test ProjectStatus enum values."""
        from src.models.project import ProjectStatus
        
        assert ProjectStatus.DRAFT.value == "draft"
        assert ProjectStatus.ACTIVE.value == "active"
        assert ProjectStatus.COMPLETED.value == "completed"
        assert ProjectStatus.ARCHIVED.value == "archived"
    
    def test_project_response(self):
        """Test ProjectResponse model."""
        from src.models.project import ProjectResponse, ProjectStatus
        
        project = ProjectResponse(
            id=uuid4(),
            title="Test",
            status=ProjectStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        assert project.title == "Test"
        assert project.status == ProjectStatus.ACTIVE


class TestOutlineModels:
    """Test OutlineSection models."""
    
    def test_section_type_enum(self):
        """Test SectionType enum values."""
        from src.models.outline import SectionType
        
        assert SectionType.INTRODUCTION.value == "introduction"
        assert SectionType.LITERATURE_REVIEW.value == "literature_review"
        assert SectionType.METHODS.value == "methods"
        assert SectionType.RESULTS.value == "results"
        assert SectionType.DISCUSSION.value == "discussion"
        assert SectionType.CONCLUSION.value == "conclusion"
        assert SectionType.ABSTRACT.value == "abstract"
        assert SectionType.CUSTOM.value == "custom"
    
    def test_outline_section_create(self):
        """Test OutlineSectionCreate model."""
        from src.models.outline import OutlineSectionCreate, SectionType
        
        section = OutlineSectionCreate(
            title="Introduction",
            section_type=SectionType.INTRODUCTION,
        )
        
        assert section.title == "Introduction"
        assert section.section_type == SectionType.INTRODUCTION
        assert section.parent_id is None
    
    def test_outline_section_with_parent(self):
        """Test OutlineSectionCreate with parent."""
        from src.models.outline import OutlineSectionCreate, SectionType
        
        parent_id = uuid4()
        section = OutlineSectionCreate(
            title="Subsection 1",
            section_type=SectionType.CUSTOM,
            parent_id=parent_id,
        )
        
        assert section.parent_id == parent_id


class TestSourceModels:
    """Test Source-related models."""
    
    def test_author_model(self):
        """Test Author model."""
        from src.models.source import Author
        
        author = Author(name="John Doe")
        assert author.name == "John Doe"
        assert author.author_id is None
        
        author_with_id = Author(name="Jane Doe", author_id="auth123")
        assert author_with_id.author_id == "auth123"
    
    def test_ingestion_status_enum(self):
        """Test IngestionStatus enum values."""
        from src.models.source import IngestionStatus
        
        assert IngestionStatus.PENDING.value == "pending"
        assert IngestionStatus.DOWNLOADING.value == "downloading"
        assert IngestionStatus.PARSING.value == "parsing"
        assert IngestionStatus.CHUNKING.value == "chunking"
        assert IngestionStatus.INGESTING.value == "ingesting"
        assert IngestionStatus.READY.value == "ready"
        assert IngestionStatus.FAILED.value == "failed"
    
    def test_paper_search_request(self):
        """Test PaperSearchRequest model."""
        from src.models.source import PaperSearchRequest
        
        request = PaperSearchRequest(query="transformers")
        
        assert request.query == "transformers"
        assert request.limit == 20  # default
        assert request.open_access_only is False
    
    def test_paper_search_request_with_filters(self):
        """Test PaperSearchRequest with all filters."""
        from src.models.source import PaperSearchRequest
        
        request = PaperSearchRequest(
            query="neural networks",
            limit=50,
            year_from=2020,
            year_to=2023,
            open_access_only=True,
            fields_of_study=["Computer Science"],
        )
        
        assert request.year_from == 2020
        assert request.year_to == 2023
        assert request.open_access_only is True
        assert "Computer Science" in request.fields_of_study
    
    def test_paper_search_result(self):
        """Test PaperSearchResult model."""
        from src.models.source import PaperSearchResult, Author
        
        result = PaperSearchResult(
            paper_id="abc123",
            title="Test Paper",
            authors=[Author(name="Test Author")],
            source_api="semantic_scholar",
        )
        
        assert result.paper_id == "abc123"
        assert result.title == "Test Paper"
        assert len(result.authors) == 1
        assert result.is_open_access is False
    
    def test_source_create_from_search_result(self):
        """Test SourceCreate model with all fields."""
        from src.models.source import SourceCreate, Author
        
        source = SourceCreate(
            paper_id="abc123",
            title="Test Paper",
            doi="10.1234/test",
            arxiv_id="2301.00000",
            authors=[Author(name="Test Author")],
            abstract="This is a test abstract.",
            publication_year=2023,
            venue="NeurIPS",
            pdf_url="https://example.com/paper.pdf",
        )
        
        assert source.doi == "10.1234/test"
        assert source.arxiv_id == "2301.00000"
        assert source.publication_year == 2023


class TestHyperionModels:
    """Test Hyperion-related models."""
    
    def test_document_status_enum(self):
        """Test DocumentStatus enum values."""
        from src.models.hyperion import DocumentStatus
        
        assert DocumentStatus.PROCESSED.value == "processed"
        assert DocumentStatus.FAILED.value == "failed"
        assert DocumentStatus.PROCESSING.value == "processing"
    
    def test_hyperion_document(self):
        """Test HyperionDocument model."""
        from src.models.hyperion import HyperionDocument, DocumentStatus
        
        doc = HyperionDocument(name="test_paper.pdf")
        
        assert doc.name == "test_paper.pdf"
        assert doc.status == DocumentStatus.PROCESSED  # default
    
    def test_ingest_request(self):
        """Test IngestRequest model."""
        from src.models.hyperion import IngestRequest
        
        request = IngestRequest(
            texts=["chunk 1", "chunk 2", "chunk 3"],
            doc_name="test_doc",
        )
        
        assert len(request.texts) == 3
        assert request.doc_name == "test_doc"
        # Test doc_names property
        assert request.doc_names == ["test_doc", "test_doc", "test_doc"]
    
    def test_query_result(self):
        """Test QueryResult model."""
        from src.models.hyperion import QueryResult, ChunkReference
        
        result = QueryResult(
            success=True,
            query="What is attention?",
            response="Attention is a mechanism...",
            sources=[
                ChunkReference(doc_name="paper1.pdf"),
                ChunkReference(doc_name="paper2.pdf"),
            ],
        )
        
        assert result.success is True
        assert len(result.sources) == 2
        assert result.error is None
    
    def test_upload_result(self):
        """Test UploadResult model."""
        from src.models.hyperion import UploadResult
        
        result = UploadResult(
            success=True,
            filename="paper.pdf",
            doc_id="doc-12345",
            status="processing",
        )
        
        assert result.success is True
        assert result.filename == "paper.pdf"
        assert result.doc_id == "doc-12345"
        assert result.status == "processing"
    
    def test_pipeline_status(self):
        """Test PipelineStatus model."""
        from src.models.hyperion import PipelineStatus
        
        status = PipelineStatus(
            busy=False,
            docs_count=5,
            latest_message="Completed successfully",
        )
        
        assert status.busy is False
        assert status.docs_count == 5
        assert status.latest_message == "Completed successfully"


class TestResearchModels:
    """Test Research/Query models."""
    
    def test_query_request(self):
        """Test QueryRequest model."""
        from src.models.research import QueryRequest, QueryMode, CitationStyle
        
        request = QueryRequest(
            query="What are the key findings?",
        )
        
        assert request.query == "What are the key findings?"
        assert request.mode == QueryMode.SIMPLE  # default
        assert request.citation_style == CitationStyle.APA  # default
    
    def test_source_reference(self):
        """Test SourceReference model."""
        from src.models.research import SourceReference
        
        ref = SourceReference(
            source_id=uuid4(),
            title="Test Paper",
            authors=["Author One", "Author Two"],
            retrieved_text="This is a relevant quote.",
            relevance_score=0.85,
        )
        
        assert ref.title == "Test Paper"
        assert ref.relevance_score == 0.85
        assert len(ref.authors) == 2
    
    def test_query_response(self):
        """Test QueryResponse model."""
        from src.models.research import QueryResponse, SourceReference
        
        response = QueryResponse(
            query="What is attention?",
            answer="Attention is a mechanism that...",
            sources=[],
        )
        
        assert response.answer == "Attention is a mechanism that..."
        assert response.total_chunks_searched == 0  # default
    
    def test_query_mode_enum(self):
        """Test QueryMode enum values."""
        from src.models.research import QueryMode
        
        assert QueryMode.SIMPLE.value == "simple"
        assert QueryMode.HYBRID.value == "hybrid"
        assert QueryMode.MULTI_HOP.value == "multi_hop"
    
    def test_citation_style_enum(self):
        """Test CitationStyle enum values."""
        from src.models.research import CitationStyle
        
        assert CitationStyle.APA.value == "apa"
        assert CitationStyle.MLA.value == "mla"
        assert CitationStyle.IEEE.value == "ieee"


class TestModelValidation:
    """Test model validation edge cases."""
    
    def test_empty_title_rejected(self):
        """Test that empty titles are rejected."""
        from src.models.project import ProjectCreate
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            ProjectCreate(title="")
    
    def test_search_limit_bounds(self):
        """Test search limit validation."""
        from src.models.source import PaperSearchRequest
        from pydantic import ValidationError
        
        # Valid range
        request = PaperSearchRequest(query="test", limit=50)
        assert request.limit == 50
        
        # Should accept edge values
        request_min = PaperSearchRequest(query="test", limit=1)
        assert request_min.limit == 1
        
        request_max = PaperSearchRequest(query="test", limit=100)
        assert request_max.limit == 100
    
    def test_ingest_request_min_texts(self):
        """Test IngestRequest requires at least one text."""
        from src.models.hyperion import IngestRequest
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            IngestRequest(texts=[], doc_name="test")
