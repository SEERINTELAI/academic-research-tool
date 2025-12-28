"""
PDF Processor for academic papers.

Handles:
1. PDF download from arXiv, Unpaywall, direct URLs
2. GROBID parsing for structure extraction
3. Coordination with source ingestion pipeline
"""

import logging
import re
from typing import Optional
from uuid import UUID

import httpx

from src.config import get_settings
from src.models.source import Author, IngestionStatus
from src.services.database import get_supabase_client
from src.services.grobid_client import GrobidClient, GrobidError, ParsedPaper

logger = logging.getLogger(__name__)

# User agent for PDF downloads
USER_AGENT = "AcademicResearchTool/0.1.0 (mailto:research@example.com)"

# arXiv PDF URL patterns
ARXIV_PDF_PATTERN = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d+\.\d+)", re.IGNORECASE)
ARXIV_PDF_URL_TEMPLATE = "https://arxiv.org/pdf/{arxiv_id}.pdf"


class PDFProcessorError(Exception):
    """PDF processing error."""
    
    def __init__(self, message: str, source_id: Optional[UUID] = None):
        self.message = message
        self.source_id = source_id
        super().__init__(self.message)


class PDFProcessor:
    """
    Processor for downloading and parsing academic PDFs.
    
    Usage:
        processor = PDFProcessor()
        paper = await processor.process_source(source_id)
    """
    
    def __init__(self, timeout: float = 60.0):
        """
        Initialize PDF processor.
        
        Args:
            timeout: Download timeout in seconds.
        """
        self.settings = get_settings()
        self.timeout = timeout
        self.db = get_supabase_client()
    
    async def download_pdf(
        self,
        url: str,
        arxiv_id: Optional[str] = None,
        doi: Optional[str] = None,
    ) -> bytes:
        """
        Download PDF from URL, arXiv ID, or DOI.
        
        Tries multiple sources in order:
        1. Direct URL if provided
        2. arXiv if arxiv_id provided
        3. Unpaywall lookup if DOI provided
        
        Args:
            url: Direct PDF URL.
            arxiv_id: arXiv identifier (e.g., "2301.00000").
            doi: DOI for Unpaywall lookup.
        
        Returns:
            PDF content as bytes.
        
        Raises:
            PDFProcessorError: If download fails.
        """
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            # Try direct URL first
            if url:
                try:
                    logger.info(f"Downloading PDF from: {url}")
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        content_type = response.headers.get("content-type", "")
                        if "pdf" in content_type or url.endswith(".pdf"):
                            return response.content
                        else:
                            logger.warning(f"URL didn't return PDF: {content_type}")
                except httpx.HTTPError as e:
                    logger.warning(f"Direct URL failed: {e}")
            
            # Try arXiv
            if arxiv_id:
                try:
                    # Clean arxiv ID
                    clean_id = arxiv_id.replace("arXiv:", "").strip()
                    arxiv_url = ARXIV_PDF_URL_TEMPLATE.format(arxiv_id=clean_id)
                    
                    logger.info(f"Downloading from arXiv: {arxiv_url}")
                    response = await client.get(arxiv_url)
                    
                    if response.status_code == 200:
                        return response.content
                except httpx.HTTPError as e:
                    logger.warning(f"arXiv download failed: {e}")
            
            # Try Unpaywall
            if doi:
                try:
                    oa_url = await self._get_unpaywall_pdf(client, doi)
                    if oa_url:
                        logger.info(f"Downloading from Unpaywall: {oa_url}")
                        response = await client.get(oa_url)
                        
                        if response.status_code == 200:
                            return response.content
                except httpx.HTTPError as e:
                    logger.warning(f"Unpaywall download failed: {e}")
        
        raise PDFProcessorError("Failed to download PDF from any source")
    
    async def _get_unpaywall_pdf(
        self,
        client: httpx.AsyncClient,
        doi: str,
    ) -> Optional[str]:
        """
        Look up open access PDF URL via Unpaywall.
        
        Args:
            client: HTTP client.
            doi: DOI to look up.
        
        Returns:
            PDF URL if available, None otherwise.
        """
        # Unpaywall API requires email
        email = "research@example.com"  # TODO: make configurable
        url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
        
        try:
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                # Try best OA location first
                best_oa = data.get("best_oa_location")
                if best_oa and best_oa.get("url_for_pdf"):
                    return best_oa["url_for_pdf"]
                
                # Try any OA location
                for loc in data.get("oa_locations", []):
                    if loc.get("url_for_pdf"):
                        return loc["url_for_pdf"]
        except Exception as e:
            logger.warning(f"Unpaywall lookup failed: {e}")
        
        return None
    
    async def parse_pdf(self, pdf_content: bytes) -> ParsedPaper:
        """
        Parse PDF using GROBID.
        
        Args:
            pdf_content: PDF bytes.
        
        Returns:
            ParsedPaper with extracted structure.
        """
        async with GrobidClient() as grobid:
            return await grobid.parse_pdf(pdf_content)
    
    async def process_source(self, source_id: UUID) -> ParsedPaper:
        """
        Process a source: download PDF, parse with GROBID.
        
        Updates source status in database during processing.
        
        Args:
            source_id: Source ID from database.
        
        Returns:
            ParsedPaper with extracted content.
        
        Raises:
            PDFProcessorError: If processing fails.
        """
        # Get source from database
        source_result = self.db.table("source")\
            .select("*")\
            .eq("id", str(source_id))\
            .single()\
            .execute()
        
        if not source_result.data:
            raise PDFProcessorError(f"Source not found: {source_id}", source_id)
        
        source = source_result.data
        
        try:
            # Update status to downloading
            self._update_source_status(source_id, IngestionStatus.DOWNLOADING)
            
            # Download PDF
            pdf_content = await self.download_pdf(
                url=source.get("pdf_url"),
                arxiv_id=source.get("arxiv_id"),
                doi=source.get("doi"),
            )
            
            logger.info(f"Downloaded PDF for {source_id}: {len(pdf_content)} bytes")
            
            # Update status to parsing
            self._update_source_status(source_id, IngestionStatus.PARSING)
            
            # Parse with GROBID
            paper = await self.parse_pdf(pdf_content)
            
            logger.info(
                f"Parsed {source_id}: {paper.title}, "
                f"{len(paper.sections)} sections, "
                f"{len(paper.references)} references"
            )
            
            # Update source with parsed metadata if we got better data
            self._update_source_metadata(source_id, paper)
            
            return paper
            
        except GrobidError as e:
            self._update_source_status(
                source_id,
                IngestionStatus.FAILED,
                error_message=f"GROBID parsing failed: {e.message}",
            )
            raise PDFProcessorError(f"GROBID error: {e.message}", source_id)
            
        except PDFProcessorError as e:
            self._update_source_status(
                source_id,
                IngestionStatus.FAILED,
                error_message=e.message,
            )
            raise
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.exception(error_msg)
            self._update_source_status(
                source_id,
                IngestionStatus.FAILED,
                error_message=error_msg,
            )
            raise PDFProcessorError(error_msg, source_id)
    
    def _update_source_status(
        self,
        source_id: UUID,
        status: IngestionStatus,
        error_message: Optional[str] = None,
    ) -> None:
        """Update source ingestion status in database."""
        update_data = {"ingestion_status": status.value}
        if error_message:
            update_data["error_message"] = error_message
        
        self.db.table("source")\
            .update(update_data)\
            .eq("id", str(source_id))\
            .execute()
    
    def _update_source_metadata(
        self,
        source_id: UUID,
        paper: ParsedPaper,
    ) -> None:
        """Update source metadata from parsed paper."""
        update_data = {}
        
        # Only update if GROBID found better data
        if paper.title:
            update_data["title"] = paper.title
        
        if paper.authors:
            update_data["authors"] = [
                {
                    "name": a.full_name,
                    "affiliation": a.affiliation,
                }
                for a in paper.authors
            ]
        
        if paper.abstract:
            update_data["abstract"] = paper.abstract
        
        if paper.keywords:
            update_data["keywords"] = paper.keywords
        
        if update_data:
            self.db.table("source")\
                .update(update_data)\
                .eq("id", str(source_id))\
                .execute()


# Convenience functions
async def download_and_parse_pdf(
    url: str,
    arxiv_id: Optional[str] = None,
    doi: Optional[str] = None,
) -> ParsedPaper:
    """Download and parse a PDF."""
    processor = PDFProcessor()
    pdf_content = await processor.download_pdf(url, arxiv_id, doi)
    return await processor.parse_pdf(pdf_content)


async def process_source(source_id: UUID) -> ParsedPaper:
    """Process a source by ID."""
    processor = PDFProcessor()
    return await processor.process_source(source_id)

