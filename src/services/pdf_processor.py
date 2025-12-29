"""
PDF Processor for academic papers.

Simplified version: downloads PDFs only.
LightRAG handles parsing and chunking automatically.
"""

import logging
import re
from typing import Optional
from uuid import UUID

import httpx

from src.config import get_settings

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


class PDFDownloader:
    """
    Downloads academic PDFs from various sources.
    
    Tries multiple sources:
    1. Direct URL
    2. arXiv
    3. Unpaywall (for OA PDFs via DOI)
    
    Usage:
        downloader = PDFDownloader()
        pdf_bytes = await downloader.download(url, arxiv_id, doi)
    """
    
    def __init__(self, timeout: float = 60.0):
        """
        Initialize PDF downloader.
        
        Args:
            timeout: Download timeout in seconds.
        """
        self.settings = get_settings()
        self.timeout = timeout
    
    async def download(
        self,
        url: Optional[str] = None,
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
            PDFProcessorError: If download fails from all sources.
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
                            logger.info(f"Downloaded {len(response.content)} bytes from URL")
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
                        logger.info(f"Downloaded {len(response.content)} bytes from arXiv")
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
                            logger.info(f"Downloaded {len(response.content)} bytes from Unpaywall")
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
    
    def generate_filename(
        self,
        title: Optional[str] = None,
        arxiv_id: Optional[str] = None,
        doi: Optional[str] = None,
    ) -> str:
        """
        Generate a filename for the PDF.
        
        Args:
            title: Paper title.
            arxiv_id: arXiv ID.
            doi: DOI.
        
        Returns:
            Sanitized filename with .pdf extension.
        """
        if title:
            # Sanitize title for filename
            safe_title = re.sub(r'[^\w\s-]', '', title)
            safe_title = re.sub(r'\s+', '_', safe_title)
            safe_title = safe_title[:100]  # Limit length
            return f"{safe_title}.pdf"
        elif arxiv_id:
            clean_id = arxiv_id.replace("arXiv:", "").replace("/", "_")
            return f"arxiv_{clean_id}.pdf"
        elif doi:
            clean_doi = doi.replace("/", "_").replace(":", "_")
            return f"doi_{clean_doi}.pdf"
        else:
            return "document.pdf"


# Convenience function
async def download_pdf(
    url: Optional[str] = None,
    arxiv_id: Optional[str] = None,
    doi: Optional[str] = None,
) -> bytes:
    """Download a PDF from various sources."""
    downloader = PDFDownloader()
    return await downloader.download(url, arxiv_id, doi)
