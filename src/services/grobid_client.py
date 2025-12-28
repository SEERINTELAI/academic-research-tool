"""
GROBID Client for academic PDF parsing.

GROBID (GeneRation Of BIbliographic Data) extracts structured data
from academic PDFs including:
- Title, authors, abstract
- Section structure
- References
- Figure/table captions

Uses public GROBID endpoint or self-hosted instance.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from xml.etree import ElementTree as ET

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)

# TEI XML namespaces used by GROBID
TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


class SectionType(str, Enum):
    """Academic paper section types."""
    
    TITLE = "title"
    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    RELATED_WORK = "related_work"
    METHODS = "methods"
    EXPERIMENTS = "experiments"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    ACKNOWLEDGMENTS = "acknowledgments"
    REFERENCES = "references"
    APPENDIX = "appendix"
    UNKNOWN = "unknown"


@dataclass
class Author:
    """Parsed author information."""
    
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    affiliation: Optional[str] = None
    
    @property
    def full_name(self) -> str:
        """Get full name."""
        parts = [p for p in [self.first_name, self.last_name] if p]
        return " ".join(parts) if parts else "Unknown"


@dataclass
class Reference:
    """Parsed bibliographic reference."""
    
    index: int
    title: Optional[str] = None
    authors: list[str] = field(default_factory=list)
    year: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    raw_text: Optional[str] = None


@dataclass
class Section:
    """Parsed document section."""
    
    section_type: SectionType
    title: Optional[str] = None
    text: str = ""
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    subsections: list["Section"] = field(default_factory=list)


@dataclass
class ParsedPaper:
    """Complete parsed paper structure."""
    
    title: Optional[str] = None
    authors: list[Author] = field(default_factory=list)
    abstract: Optional[str] = None
    keywords: list[str] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    raw_tei: Optional[str] = None
    
    @property
    def full_text(self) -> str:
        """Get concatenated full text."""
        parts = []
        if self.abstract:
            parts.append(f"Abstract\n\n{self.abstract}")
        for section in self.sections:
            if section.title:
                parts.append(f"\n\n{section.title}\n\n{section.text}")
            else:
                parts.append(f"\n\n{section.text}")
        return "\n".join(parts)


class GrobidError(Exception):
    """GROBID processing error."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class GrobidClient:
    """
    Client for GROBID PDF parsing service.
    
    Default uses public Hugging Face endpoint (free, slower).
    For production, deploy your own GROBID instance.
    
    Usage:
        async with GrobidClient() as client:
            paper = await client.parse_pdf(pdf_bytes)
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 120.0,  # PDF parsing can be slow
    ):
        """
        Initialize GROBID client.
        
        Args:
            base_url: GROBID service URL (default: HuggingFace endpoint).
            timeout: Request timeout in seconds.
        """
        settings = get_settings()
        self.base_url = base_url or settings.grobid_url
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> "GrobidClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def is_alive(self) -> bool:
        """Check if GROBID service is available."""
        if not self._client:
            raise GrobidError("Client not initialized")
        
        try:
            response = await self._client.get("/api/isalive")
            return response.status_code == 200
        except Exception:
            return False
    
    async def parse_pdf(
        self,
        pdf_content: bytes,
        consolidate_citations: bool = True,
        include_raw_citations: bool = True,
    ) -> ParsedPaper:
        """
        Parse a PDF and extract structured content.
        
        Args:
            pdf_content: Raw PDF bytes.
            consolidate_citations: Consolidate citation info with header.
            include_raw_citations: Include raw citation strings.
        
        Returns:
            ParsedPaper with extracted structure.
        
        Raises:
            GrobidError: If parsing fails.
        """
        if not self._client:
            raise GrobidError("Client not initialized")
        
        # Build form data
        files = {"input": ("paper.pdf", pdf_content, "application/pdf")}
        data = {
            "consolidateHeader": "1" if consolidate_citations else "0",
            "consolidateCitations": "1" if consolidate_citations else "0",
            "includeRawCitations": "1" if include_raw_citations else "0",
        }
        
        try:
            logger.info("Sending PDF to GROBID for parsing...")
            response = await self._client.post(
                "/api/processFulltextDocument",
                files=files,
                data=data,
            )
            
            if response.status_code != 200:
                raise GrobidError(
                    f"GROBID returned {response.status_code}: {response.text[:200]}",
                    response.status_code,
                )
            
            tei_xml = response.text
            logger.info(f"Received TEI XML ({len(tei_xml)} bytes)")
            
            return self._parse_tei(tei_xml)
            
        except httpx.HTTPError as e:
            logger.exception(f"HTTP error calling GROBID: {e}")
            raise GrobidError(f"HTTP error: {e}")
    
    async def parse_header(self, pdf_content: bytes) -> ParsedPaper:
        """
        Parse only the header (title, authors, abstract).
        
        Faster than full parse when you only need metadata.
        """
        if not self._client:
            raise GrobidError("Client not initialized")
        
        files = {"input": ("paper.pdf", pdf_content, "application/pdf")}
        
        try:
            response = await self._client.post(
                "/api/processHeaderDocument",
                files=files,
            )
            
            if response.status_code != 200:
                raise GrobidError(
                    f"GROBID header parse failed: {response.text[:200]}",
                    response.status_code,
                )
            
            return self._parse_tei(response.text, header_only=True)
            
        except httpx.HTTPError as e:
            raise GrobidError(f"HTTP error: {e}")
    
    def _parse_tei(self, tei_xml: str, header_only: bool = False) -> ParsedPaper:
        """
        Parse TEI XML into structured data.
        
        Args:
            tei_xml: Raw TEI XML from GROBID.
            header_only: If True, skip body parsing.
        
        Returns:
            ParsedPaper with extracted data.
        """
        try:
            root = ET.fromstring(tei_xml)
        except ET.ParseError as e:
            logger.error(f"Failed to parse TEI XML: {e}")
            raise GrobidError(f"Invalid TEI XML: {e}")
        
        paper = ParsedPaper(raw_tei=tei_xml)
        
        # Parse header
        self._parse_header_info(root, paper)
        
        if not header_only:
            # Parse body sections
            self._parse_body(root, paper)
            
            # Parse references
            self._parse_references(root, paper)
        
        return paper
    
    def _parse_header_info(self, root: ET.Element, paper: ParsedPaper) -> None:
        """Extract title, authors, abstract from header."""
        # Title
        title_elem = root.find(".//tei:titleStmt/tei:title", TEI_NS)
        if title_elem is not None and title_elem.text:
            paper.title = title_elem.text.strip()
        
        # Authors
        for author_elem in root.findall(".//tei:sourceDesc//tei:author", TEI_NS):
            author = Author()
            
            # Name parts
            forename = author_elem.find(".//tei:forename", TEI_NS)
            surname = author_elem.find(".//tei:surname", TEI_NS)
            
            if forename is not None and forename.text:
                author.first_name = forename.text.strip()
            if surname is not None and surname.text:
                author.last_name = surname.text.strip()
            
            # Email
            email_elem = author_elem.find(".//tei:email", TEI_NS)
            if email_elem is not None and email_elem.text:
                author.email = email_elem.text.strip()
            
            # Affiliation
            aff_elem = author_elem.find(".//tei:affiliation/tei:orgName", TEI_NS)
            if aff_elem is not None and aff_elem.text:
                author.affiliation = aff_elem.text.strip()
            
            if author.first_name or author.last_name:
                paper.authors.append(author)
        
        # Abstract
        abstract_elem = root.find(".//tei:profileDesc/tei:abstract", TEI_NS)
        if abstract_elem is not None:
            # Get all text content
            abstract_text = "".join(abstract_elem.itertext())
            paper.abstract = " ".join(abstract_text.split()).strip()
        
        # Keywords
        for kw_elem in root.findall(".//tei:keywords/tei:term", TEI_NS):
            if kw_elem.text:
                paper.keywords.append(kw_elem.text.strip())
    
    def _parse_body(self, root: ET.Element, paper: ParsedPaper) -> None:
        """Extract body sections."""
        body = root.find(".//tei:body", TEI_NS)
        if body is None:
            return
        
        for div in body.findall(".//tei:div", TEI_NS):
            section = self._parse_div(div)
            if section:
                paper.sections.append(section)
    
    def _parse_div(self, div: ET.Element) -> Optional[Section]:
        """Parse a single div element into a Section."""
        # Get section heading
        head = div.find("tei:head", TEI_NS)
        title = head.text.strip() if head is not None and head.text else None
        
        # Determine section type from title
        section_type = self._classify_section(title)
        
        # Get all paragraph text
        paragraphs = []
        for p in div.findall(".//tei:p", TEI_NS):
            text = "".join(p.itertext())
            cleaned = " ".join(text.split()).strip()
            if cleaned:
                paragraphs.append(cleaned)
        
        if not paragraphs and not title:
            return None
        
        return Section(
            section_type=section_type,
            title=title,
            text="\n\n".join(paragraphs),
        )
    
    def _classify_section(self, title: Optional[str]) -> SectionType:
        """Classify section based on title."""
        if not title:
            return SectionType.UNKNOWN
        
        title_lower = title.lower().strip()
        
        # Common patterns
        patterns = {
            SectionType.INTRODUCTION: ["introduction", "intro", "1. introduction"],
            SectionType.RELATED_WORK: ["related work", "background", "prior work", "literature"],
            SectionType.METHODS: ["method", "approach", "model", "architecture", "framework"],
            SectionType.EXPERIMENTS: ["experiment", "evaluation", "setup", "implementation"],
            SectionType.RESULTS: ["result", "finding", "analysis"],
            SectionType.DISCUSSION: ["discussion", "limitation", "future work"],
            SectionType.CONCLUSION: ["conclusion", "summary", "concluding"],
            SectionType.ACKNOWLEDGMENTS: ["acknowledgment", "acknowledgement", "thanks"],
            SectionType.APPENDIX: ["appendix", "supplementary", "appendices"],
        }
        
        for section_type, keywords in patterns.items():
            for keyword in keywords:
                if keyword in title_lower:
                    return section_type
        
        return SectionType.UNKNOWN
    
    def _parse_references(self, root: ET.Element, paper: ParsedPaper) -> None:
        """Extract bibliographic references."""
        for idx, bib in enumerate(root.findall(".//tei:listBibl/tei:biblStruct", TEI_NS)):
            ref = Reference(index=idx + 1)
            
            # Title
            title_elem = bib.find(".//tei:title[@level='a']", TEI_NS)
            if title_elem is None:
                title_elem = bib.find(".//tei:title", TEI_NS)
            if title_elem is not None:
                ref.title = "".join(title_elem.itertext()).strip()
            
            # Authors
            for author in bib.findall(".//tei:author", TEI_NS):
                forename = author.find("tei:persName/tei:forename", TEI_NS)
                surname = author.find("tei:persName/tei:surname", TEI_NS)
                
                name_parts = []
                if forename is not None and forename.text:
                    name_parts.append(forename.text.strip())
                if surname is not None and surname.text:
                    name_parts.append(surname.text.strip())
                
                if name_parts:
                    ref.authors.append(" ".join(name_parts))
            
            # Year
            date_elem = bib.find(".//tei:date[@type='published']", TEI_NS)
            if date_elem is None:
                date_elem = bib.find(".//tei:date", TEI_NS)
            if date_elem is not None:
                ref.year = date_elem.get("when", date_elem.text)
            
            # Journal/venue
            journal_elem = bib.find(".//tei:title[@level='j']", TEI_NS)
            if journal_elem is not None and journal_elem.text:
                ref.journal = journal_elem.text.strip()
            
            # DOI
            doi_elem = bib.find(".//tei:idno[@type='DOI']", TEI_NS)
            if doi_elem is not None and doi_elem.text:
                ref.doi = doi_elem.text.strip()
            
            # Raw citation text
            raw_elem = bib.find(".//tei:note[@type='raw_reference']", TEI_NS)
            if raw_elem is not None:
                ref.raw_text = "".join(raw_elem.itertext()).strip()
            
            paper.references.append(ref)


# Convenience function
async def parse_pdf(pdf_content: bytes) -> ParsedPaper:
    """Parse PDF content (convenience function)."""
    async with GrobidClient() as client:
        return await client.parse_pdf(pdf_content)

