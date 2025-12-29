"""
Report/Paper Generation API routes.

Endpoints for generating academic papers from outline and sources.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel, Field

from src.api.deps import DatabaseDep, CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class Citation(BaseModel):
    """In-text citation model."""
    source_id: UUID
    source_title: str
    authors: list[str]
    year: Optional[int] = None
    position: int = 0  # Position in text (character offset)


class SectionDraft(BaseModel):
    """Generated section draft."""
    section_id: UUID
    title: str
    content: str
    citations: list[Citation] = []
    word_count: int = 0


class GenerateReportRequest(BaseModel):
    """Request to generate a paper."""
    include_bibliography: bool = True
    citation_style: str = Field(default="apa", pattern="^(apa|mla|chicago|ieee)$")


class GenerateReportResponse(BaseModel):
    """Response from report generation."""
    project_id: UUID
    content: str
    sections: list[SectionDraft]
    bibliography: Optional[str] = None
    total_citations: int = 0
    word_count: int = 0
    generated_at: datetime


class ReportResponse(BaseModel):
    """Saved report response."""
    id: UUID
    project_id: UUID
    content: str
    bibliography: Optional[str] = None
    citation_style: str
    word_count: int
    created_at: datetime
    updated_at: datetime


class GenerateSectionRequest(BaseModel):
    """Request to generate a section draft."""
    max_words: int = Field(default=500, ge=100, le=3000)
    use_rag: bool = True


class GenerateSectionResponse(BaseModel):
    """Response from section generation."""
    section_id: UUID
    title: str
    content: str
    citations: list[Citation] = []
    word_count: int = 0


# =============================================================================
# Helper Functions
# =============================================================================

async def get_project_sources(db: DatabaseDep, project_id: UUID) -> list[dict]:
    """Get all ingested sources for a project."""
    result = db.table("source")\
        .select("id, title, authors, publication_year, doi, arxiv_id, abstract")\
        .eq("project_id", str(project_id))\
        .eq("ingestion_status", "ready")\
        .execute()
    return result.data or []


async def get_project_outline(db: DatabaseDep, project_id: UUID) -> list[dict]:
    """Get outline sections for a project."""
    result = db.table("outline_section")\
        .select("*")\
        .eq("project_id", str(project_id))\
        .order("order_index")\
        .execute()
    return result.data or []


def format_citation_apa(authors: list, year: Optional[int], title: str) -> str:
    """Format a citation in APA style."""
    if not authors:
        author_str = "Unknown"
    elif len(authors) == 1:
        author_str = authors[0].get("name", "Unknown") if isinstance(authors[0], dict) else authors[0]
    elif len(authors) == 2:
        names = [a.get("name", "Unknown") if isinstance(a, dict) else a for a in authors]
        author_str = f"{names[0]} & {names[1]}"
    else:
        first_author = authors[0].get("name", "Unknown") if isinstance(authors[0], dict) else authors[0]
        author_str = f"{first_author} et al."
    
    year_str = str(year) if year else "n.d."
    return f"{author_str} ({year_str})"


def format_bibliography_entry_apa(source: dict) -> str:
    """Format a bibliography entry in APA style."""
    authors = source.get("authors", [])
    year = source.get("publication_year")
    title = source.get("title", "Untitled")
    
    # Format author names
    if not authors:
        author_str = "Unknown."
    else:
        author_names = []
        for a in authors[:7]:  # APA limits to 7 authors
            if isinstance(a, dict):
                name = a.get("name", "Unknown")
            else:
                name = str(a)
            author_names.append(name)
        
        if len(authors) > 7:
            author_str = ", ".join(author_names[:6]) + ", ... " + author_names[-1] + "."
        else:
            author_str = ", ".join(author_names) + "."
    
    year_str = f"({year})." if year else "(n.d.)."
    
    # Build entry
    doi = source.get("doi")
    doi_str = f" https://doi.org/{doi}" if doi else ""
    
    return f"{author_str} {year_str} {title}.{doi_str}"


async def generate_section_content(
    db: DatabaseDep,
    project_id: UUID,
    section: dict,
    sources: list[dict],
    max_words: int = 500,
) -> tuple[str, list[Citation]]:
    """
    Generate content for a section using available sources.
    
    Returns tuple of (content, citations).
    """
    section_title = section.get("title", "Section")
    section_type = section.get("section_type", "custom")
    
    citations = []
    content_parts = []
    
    if section_type == "introduction":
        content_parts.append(
            f"This paper presents a comprehensive analysis of the topic. "
            f"The following sections outline our research methodology and key findings."
        )
        
    elif section_type == "literature_review":
        content_parts.append(
            f"Previous research has explored various aspects of this domain. "
        )
        
        # Reference sources
        for i, source in enumerate(sources[:5]):
            citation = Citation(
                source_id=UUID(source["id"]),
                source_title=source["title"],
                authors=[a.get("name", "") if isinstance(a, dict) else a for a in source.get("authors", [])[:3]],
                year=source.get("publication_year"),
                position=len(" ".join(content_parts)),
            )
            citations.append(citation)
            
            cite_str = format_citation_apa(source.get("authors", []), source.get("publication_year"), source["title"])
            
            if source.get("abstract"):
                summary = source["abstract"][:200] + "..." if len(source.get("abstract", "")) > 200 else source.get("abstract", "")
                content_parts.append(
                    f"{cite_str} investigated this topic, finding that {summary.lower()} "
                )
            else:
                content_parts.append(
                    f"{cite_str} contributed to our understanding of this field. "
                )
        
    elif section_type == "methods":
        content_parts.append(
            f"Our methodology involved a systematic review of the literature. "
            f"We collected and analyzed papers from major academic databases."
        )
        
    elif section_type == "results":
        content_parts.append(
            f"The analysis revealed several key findings. "
        )
        
        for source in sources[:3]:
            citation = Citation(
                source_id=UUID(source["id"]),
                source_title=source["title"],
                authors=[a.get("name", "") if isinstance(a, dict) else a for a in source.get("authors", [])[:3]],
                year=source.get("publication_year"),
                position=len(" ".join(content_parts)),
            )
            citations.append(citation)
            
            cite_str = format_citation_apa(source.get("authors", []), source.get("publication_year"), source["title"])
            content_parts.append(f"According to {cite_str}, significant progress has been made. ")
        
    elif section_type == "discussion":
        content_parts.append(
            f"These findings have important implications for the field. "
            f"Future research should explore these topics in greater depth."
        )
        
    elif section_type == "conclusion":
        content_parts.append(
            f"In conclusion, this paper has examined the key aspects of the topic. "
            f"The evidence suggests that continued research is warranted."
        )
        
    else:
        # Custom section
        content_parts.append(f"This section covers {section_title.lower()}. ")
        
        for source in sources[:2]:
            citation = Citation(
                source_id=UUID(source["id"]),
                source_title=source["title"],
                authors=[a.get("name", "") if isinstance(a, dict) else a for a in source.get("authors", [])[:3]],
                year=source.get("publication_year"),
                position=len(" ".join(content_parts)),
            )
            citations.append(citation)
    
    content = " ".join(content_parts)
    
    # Truncate to max_words
    words = content.split()
    if len(words) > max_words:
        content = " ".join(words[:max_words]) + "..."
    
    return content, citations


# =============================================================================
# API Endpoints
# =============================================================================

@router.post(
    "/generate",
    response_model=GenerateReportResponse,
    summary="Generate a paper from outline",
    description="Generate a complete paper draft using the project outline and ingested sources.",
)
async def generate_report(
    user: CurrentUser,
    db: DatabaseDep,
    project_id: UUID = Path(..., description="Project ID"),
    request: GenerateReportRequest = GenerateReportRequest(),
) -> GenerateReportResponse:
    """Generate a paper from the outline and sources."""
    logger.info(f"Generating report for project {project_id}")
    
    # Get outline sections
    outline = await get_project_outline(db, project_id)
    if not outline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No outline found. Please create an outline first.",
        )
    
    # Get ingested sources
    sources = await get_project_sources(db, project_id)
    if not sources:
        logger.warning(f"No ingested sources for project {project_id}")
    
    # Generate each section
    all_sections = []
    all_content_parts = []
    all_citations = []
    
    for section in outline:
        content, citations = await generate_section_content(
            db, project_id, section, sources
        )
        
        section_draft = SectionDraft(
            section_id=UUID(section["id"]),
            title=section["title"],
            content=content,
            citations=citations,
            word_count=len(content.split()),
        )
        all_sections.append(section_draft)
        
        # Add to full content
        all_content_parts.append(f"## {section['title']}\n\n{content}\n")
        all_citations.extend(citations)
    
    # Build full content
    full_content = "\n".join(all_content_parts)
    
    # Generate bibliography
    bibliography = None
    if request.include_bibliography and sources:
        bib_entries = []
        for source in sources:
            entry = format_bibliography_entry_apa(source)
            bib_entries.append(entry)
        
        bibliography = "## References\n\n" + "\n\n".join(sorted(bib_entries))
        full_content += "\n\n" + bibliography
    
    word_count = len(full_content.split())
    
    # Save report to database
    try:
        db.table("report").upsert({
            "project_id": str(project_id),
            "content": full_content,
            "bibliography": bibliography,
            "citation_style": request.citation_style,
            "word_count": word_count,
        }).execute()
    except Exception as e:
        logger.warning(f"Could not save report to database: {e}")
    
    return GenerateReportResponse(
        project_id=project_id,
        content=full_content,
        sections=all_sections,
        bibliography=bibliography,
        total_citations=len(all_citations),
        word_count=word_count,
        generated_at=datetime.utcnow(),
    )


@router.get(
    "",
    response_model=ReportResponse,
    summary="Get generated report",
    description="Get the most recently generated report for a project.",
)
async def get_report(
    user: CurrentUser,
    db: DatabaseDep,
    project_id: UUID = Path(..., description="Project ID"),
) -> ReportResponse:
    """Get the generated report for a project."""
    result = db.table("report")\
        .select("*")\
        .eq("project_id", str(project_id))\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No report found. Generate a report first.",
        )
    
    report = result.data[0]
    
    return ReportResponse(
        id=UUID(report["id"]),
        project_id=UUID(report["project_id"]),
        content=report["content"],
        bibliography=report.get("bibliography"),
        citation_style=report.get("citation_style", "apa"),
        word_count=report.get("word_count", 0),
        created_at=report["created_at"],
        updated_at=report["updated_at"],
    )


@router.post(
    "/sections/{section_id}/write",
    response_model=GenerateSectionResponse,
    summary="Generate a section draft",
    description="Generate a draft for a specific outline section.",
)
async def generate_section_draft(
    user: CurrentUser,
    db: DatabaseDep,
    project_id: UUID = Path(..., description="Project ID"),
    section_id: UUID = Path(..., description="Section ID"),
    request: GenerateSectionRequest = GenerateSectionRequest(),
) -> GenerateSectionResponse:
    """Generate a draft for a specific section."""
    # Get section
    result = db.table("outline_section")\
        .select("*")\
        .eq("id", str(section_id))\
        .eq("project_id", str(project_id))\
        .execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found.",
        )
    
    section = result.data[0]
    
    # Get sources
    sources = await get_project_sources(db, project_id)
    
    # Generate content
    content, citations = await generate_section_content(
        db, project_id, section, sources, max_words=request.max_words
    )
    
    return GenerateSectionResponse(
        section_id=section_id,
        title=section["title"],
        content=content,
        citations=citations,
        word_count=len(content.split()),
    )

