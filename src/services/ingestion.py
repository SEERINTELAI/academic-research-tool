"""
Ingestion Service.

Simplified pipeline using LightRAG:
1. Download PDF
2. Upload to LightRAG (handles chunking automatically)
3. Track ingestion status
"""

import asyncio
import logging
from typing import Optional
from uuid import UUID

from src.config import get_settings
from src.models.source import IngestionStatus
from src.services.database import get_supabase_client
from src.services.hyperion_client import HyperionClient, HyperionError
from src.services.pdf_processor import PDFDownloader, PDFProcessorError

logger = logging.getLogger(__name__)


class IngestionError(Exception):
    """Ingestion pipeline error."""
    
    def __init__(self, message: str, source_id: Optional[UUID] = None, stage: str = "unknown"):
        self.message = message
        self.source_id = source_id
        self.stage = stage
        super().__init__(self.message)


class IngestionService:
    """
    Service for ingesting academic papers into LightRAG.
    
    Simplified flow:
    1. Download PDF from URL/arXiv/DOI
    2. Upload to LightRAG (automatic chunking + indexing)
    3. Track status via LightRAG pipeline
    
    LightRAG handles:
    - PDF parsing
    - Text extraction
    - Chunking
    - Embedding
    - Knowledge graph construction
    
    Usage:
        service = IngestionService()
        result = await service.ingest_source(source_id)
    """
    
    def __init__(self):
        """Initialize ingestion service."""
        self.db = get_supabase_client()
        self.downloader = PDFDownloader()
    
    async def ingest_source(
        self,
        source_id: UUID,
        force_reprocess: bool = False,
    ) -> dict:
        """
        Ingest a source into LightRAG.
        
        Pipeline:
        1. Download PDF
        2. Upload to LightRAG
        3. Update source with LightRAG doc ID
        
        Args:
            source_id: Source ID in database.
            force_reprocess: Force re-ingestion even if already processed.
        
        Returns:
            Dict with ingestion results.
        
        Raises:
            IngestionError: If any stage fails.
        """
        # Get source
        source = self._get_source(source_id)
        if not source:
            raise IngestionError(f"Source not found: {source_id}", source_id, "fetch")
        
        # Check if already ingested
        current_status = source.get("ingestion_status")
        if not force_reprocess and current_status == IngestionStatus.READY.value:
            logger.info(f"Source {source_id} already ingested, skipping")
            return {
                "source_id": str(source_id),
                "status": "already_ingested",
                "hyperion_doc_name": source.get("hyperion_doc_name"),
            }
        
        try:
            # Stage 1: Download PDF
            logger.info(f"Stage 1: Downloading PDF for {source_id}")
            self._update_status(source_id, IngestionStatus.DOWNLOADING)
            
            pdf_bytes = await self.downloader.download(
                url=source.get("pdf_url"),
                arxiv_id=source.get("arxiv_id"),
                doi=source.get("doi"),
            )
            
            logger.info(f"Downloaded {len(pdf_bytes)} bytes")
            
            # Generate filename for LightRAG
            filename = self.downloader.generate_filename(
                title=source.get("title"),
                arxiv_id=source.get("arxiv_id"),
                doi=source.get("doi"),
            )
            
            # Stage 2: Upload to LightRAG
            logger.info(f"Stage 2: Uploading to LightRAG as '{filename}'")
            
            async with HyperionClient() as hyperion:
                result = await hyperion.upload_pdf(pdf_bytes, filename)
            
            if not result.success:
                raise IngestionError(
                    f"LightRAG upload failed: {result.error}",
                    source_id,
                    "upload",
                )
            
            # Handle duplicate case
            if result.status == "duplicated":
                logger.info(f"Document already exists in LightRAG: {filename}")
            
            # Update source with LightRAG info
            self._update_source_complete(
                source_id=source_id,
                hyperion_doc_name=filename,
                doc_id=result.doc_id,
                track_id=result.track_id,
            )
            
            logger.info(f"Successfully uploaded {source_id} to LightRAG")
            
            return {
                "source_id": str(source_id),
                "status": "success",
                "hyperion_doc_name": filename,
                "doc_id": result.doc_id,
                "track_id": result.track_id,
                "lightrag_status": result.status,
            }
            
        except PDFProcessorError as e:
            self._update_status(source_id, IngestionStatus.FAILED, f"Download error: {e.message}")
            raise IngestionError(e.message, source_id, "download")
        
        except HyperionError as e:
            self._update_status(source_id, IngestionStatus.FAILED, f"LightRAG error: {e.message}")
            raise IngestionError(e.message, source_id, "upload")
        
        except IngestionError:
            raise
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.exception(error_msg)
            self._update_status(source_id, IngestionStatus.FAILED, error_msg)
            raise IngestionError(error_msg, source_id, "unknown")
    
    async def check_pipeline_status(self) -> dict:
        """
        Check LightRAG's processing pipeline status.
        
        Returns:
            Pipeline status dict.
        """
        async with HyperionClient() as hyperion:
            status = await hyperion.get_pipeline_status()
            return {
                "busy": status.busy,
                "job_name": status.job_name,
                "docs_count": status.docs_count,
                "current_batch": status.current_batch,
                "batches": status.batches,
                "latest_message": status.latest_message,
            }
    
    async def wait_for_processing(
        self,
        timeout: float = 300.0,
        poll_interval: float = 5.0,
    ) -> bool:
        """
        Wait for LightRAG pipeline to finish processing.
        
        Args:
            timeout: Maximum time to wait in seconds.
            poll_interval: Time between status checks.
        
        Returns:
            True if processing completed, False if timeout.
        """
        elapsed = 0.0
        
        while elapsed < timeout:
            async with HyperionClient() as hyperion:
                status = await hyperion.get_pipeline_status()
            
            if not status.busy:
                logger.info("LightRAG pipeline idle")
                return True
            
            logger.debug(f"Pipeline busy: {status.job_name} - {status.latest_message}")
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        logger.warning(f"Timeout waiting for pipeline after {timeout}s")
        return False
    
    def _get_source(self, source_id: UUID) -> Optional[dict]:
        """Get source from database."""
        result = self.db.table("source")\
            .select("*")\
            .eq("id", str(source_id))\
            .maybe_single()\
            .execute()
        return result.data
    
    def _update_status(
        self,
        source_id: UUID,
        status: IngestionStatus,
        error_message: Optional[str] = None,
    ) -> None:
        """Update source status."""
        update_data = {"ingestion_status": status.value}
        if error_message:
            update_data["error_message"] = error_message
        else:
            update_data["error_message"] = None
        
        self.db.table("source")\
            .update(update_data)\
            .eq("id", str(source_id))\
            .execute()
    
    def _update_source_complete(
        self,
        source_id: UUID,
        hyperion_doc_name: str,
        doc_id: Optional[str] = None,
        track_id: Optional[str] = None,
    ) -> None:
        """Update source as successfully uploaded to LightRAG."""
        self.db.table("source")\
            .update({
                "ingestion_status": IngestionStatus.COMPLETED.value,
                "hyperion_doc_name": hyperion_doc_name,
                "error_message": None,
            })\
            .eq("id", str(source_id))\
            .execute()
    
    async def delete_source_from_hyperion(self, source_id: UUID) -> bool:
        """
        Delete a source's document from LightRAG.
        
        Args:
            source_id: Source ID.
        
        Returns:
            True if deleted, False otherwise.
        """
        source = self._get_source(source_id)
        if not source:
            return False
        
        doc_name = source.get("hyperion_doc_name")
        if not doc_name:
            return True  # Nothing to delete
        
        async with HyperionClient() as hyperion:
            result = await hyperion.delete(doc_name)
        
        if result.success:
            # Update source status
            self.db.table("source")\
                .update({
                    "ingestion_status": IngestionStatus.PENDING.value,
                    "hyperion_doc_name": None,
                })\
                .eq("id", str(source_id))\
                .execute()
        
        return result.success


# Convenience functions
async def ingest_source(source_id: UUID, force: bool = False) -> dict:
    """Ingest a source (convenience function)."""
    service = IngestionService()
    return await service.ingest_source(source_id, force)


async def get_pipeline_status() -> dict:
    """Get LightRAG pipeline status (convenience function)."""
    service = IngestionService()
    return await service.check_pipeline_status()
