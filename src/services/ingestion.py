"""
Ingestion Service.

Orchestrates the full pipeline:
1. Download PDF
2. Parse with GROBID
3. Chunk by sections
4. Ingest chunks to Hyperion
5. Store chunk references in database
"""

import logging
from typing import Optional
from uuid import UUID

from src.config import get_settings
from src.models.chunk import ChunkForIngestion, ChunkerConfig
from src.models.source import IngestionStatus
from src.services.chunker import Chunker
from src.services.database import get_supabase_client
from src.services.grobid_client import ParsedPaper
from src.services.hyperion_client import HyperionClient, HyperionError
from src.services.pdf_processor import PDFProcessor, PDFProcessorError

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
    Service for ingesting academic papers into the RAG system.
    
    Orchestrates:
    - PDF download and parsing (PDFProcessor)
    - Chunking (Chunker)
    - Hyperion ingestion (HyperionClient)
    - Database updates
    
    Usage:
        service = IngestionService()
        result = await service.ingest_source(source_id)
    """
    
    def __init__(
        self,
        chunker_config: Optional[ChunkerConfig] = None,
        batch_size: int = 10,
    ):
        """
        Initialize ingestion service.
        
        Args:
            chunker_config: Configuration for chunking.
            batch_size: Number of chunks to ingest per batch.
        """
        self.db = get_supabase_client()
        self.pdf_processor = PDFProcessor()
        self.chunker = Chunker(chunker_config)
        self.batch_size = batch_size
    
    async def ingest_source(
        self,
        source_id: UUID,
        force_reprocess: bool = False,
    ) -> dict:
        """
        Ingest a source into Hyperion.
        
        Full pipeline:
        1. Check source status
        2. Download and parse PDF
        3. Chunk the paper
        4. Ingest chunks to Hyperion
        5. Store chunk references
        
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
        if not force_reprocess and source.get("ingestion_status") == IngestionStatus.READY.value:
            logger.info(f"Source {source_id} already ingested, skipping")
            return {
                "source_id": str(source_id),
                "status": "already_ingested",
                "chunk_count": source.get("chunk_count", 0),
            }
        
        try:
            # Stage 1: Download and parse PDF
            logger.info(f"Stage 1: Processing PDF for {source_id}")
            self._update_status(source_id, IngestionStatus.DOWNLOADING)
            
            parsed = await self.pdf_processor.process_source(source_id)
            
            # Refresh source after PDF processing updated metadata
            source = self._get_source(source_id)
            
            # Stage 2: Chunk the paper
            logger.info(f"Stage 2: Chunking for {source_id}")
            self._update_status(source_id, IngestionStatus.CHUNKING)
            
            source_metadata = {
                "doi": source.get("doi"),
                "arxiv_id": source.get("arxiv_id"),
                "publication_year": source.get("publication_year"),
                "title": source.get("title"),
            }
            
            chunks = self.chunker.chunk_paper(source_id, parsed, source_metadata)
            
            if not chunks:
                raise IngestionError("No chunks generated from paper", source_id, "chunking")
            
            logger.info(f"Generated {len(chunks)} chunks")
            
            # Stage 3: Ingest to Hyperion
            logger.info(f"Stage 3: Ingesting {len(chunks)} chunks to Hyperion")
            self._update_status(source_id, IngestionStatus.INGESTING)
            
            ingested_chunks = await self._ingest_to_hyperion(chunks)
            
            # Stage 4: Store chunk references in database
            logger.info(f"Stage 4: Storing chunk references")
            self._store_chunks(source_id, ingested_chunks)
            
            # Update source status
            self._update_source_complete(source_id, len(ingested_chunks))
            
            logger.info(f"Successfully ingested {len(ingested_chunks)} chunks for {source_id}")
            
            return {
                "source_id": str(source_id),
                "status": "success",
                "chunk_count": len(ingested_chunks),
                "title": parsed.title,
            }
            
        except PDFProcessorError as e:
            self._update_status(source_id, IngestionStatus.FAILED, f"PDF error: {e.message}")
            raise IngestionError(e.message, source_id, "pdf_processing")
        
        except HyperionError as e:
            self._update_status(source_id, IngestionStatus.FAILED, f"Hyperion error: {e.message}")
            raise IngestionError(e.message, source_id, "hyperion_ingestion")
        
        except IngestionError:
            raise
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.exception(error_msg)
            self._update_status(source_id, IngestionStatus.FAILED, error_msg)
            raise IngestionError(error_msg, source_id, "unknown")
    
    async def _ingest_to_hyperion(
        self,
        chunks: list[ChunkForIngestion],
    ) -> list[ChunkForIngestion]:
        """Ingest chunks to Hyperion in batches."""
        ingested = []
        
        async with HyperionClient() as hyperion:
            # Process in batches
            for i in range(0, len(chunks), self.batch_size):
                batch = chunks[i:i + self.batch_size]
                
                # Prepare batch for ingestion
                texts = [chunk.text for chunk in batch]
                doc_names = [chunk.doc_name for chunk in batch]
                
                try:
                    result = await hyperion.ingest(texts, doc_names)
                    
                    if result.success:
                        logger.debug(f"Batch {i // self.batch_size + 1} ingested: {result.track_id}")
                        ingested.extend(batch)
                    else:
                        logger.warning(f"Batch {i // self.batch_size + 1} failed: {result.raw_response}")
                        
                except HyperionError as e:
                    logger.error(f"Hyperion error on batch {i // self.batch_size + 1}: {e.message}")
                    raise
        
        return ingested
    
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
        
        self.db.table("source")\
            .update(update_data)\
            .eq("id", str(source_id))\
            .execute()
    
    def _update_source_complete(
        self,
        source_id: UUID,
        chunk_count: int,
    ) -> None:
        """Update source as successfully ingested."""
        self.db.table("source")\
            .update({
                "ingestion_status": IngestionStatus.READY.value,
                "chunk_count": chunk_count,
                "error_message": None,
            })\
            .eq("id", str(source_id))\
            .execute()
    
    def _store_chunks(
        self,
        source_id: UUID,
        chunks: list[ChunkForIngestion],
    ) -> None:
        """Store chunk references in database."""
        # Batch insert chunks
        chunk_rows = []
        for chunk in chunks:
            chunk_rows.append({
                "id": str(chunk.id),
                "source_id": str(source_id),
                "chunk_type": chunk.metadata.section_type or "unknown",
                "content": chunk.raw_content,
                "section_type": chunk.metadata.section_type,
                "section_title": chunk.metadata.section_title,
                "page_start": chunk.metadata.page_start,
                "page_end": chunk.metadata.page_end,
                "chunk_index": chunk.metadata.chunk_index,
                "total_chunks": chunk.metadata.total_chunks,
                "hyperion_doc_name": chunk.doc_name,
                "token_count": len(chunk.text) // 4,  # Estimate
            })
        
        if chunk_rows:
            self.db.table("chunk").insert(chunk_rows).execute()
    
    async def delete_source_from_hyperion(self, source_id: UUID) -> bool:
        """Delete all chunks for a source from Hyperion."""
        # Get chunk doc_names
        result = self.db.table("chunk")\
            .select("hyperion_doc_name")\
            .eq("source_id", str(source_id))\
            .execute()
        
        if not result.data:
            return True
        
        async with HyperionClient() as hyperion:
            for row in result.data:
                doc_name = row.get("hyperion_doc_name")
                if doc_name:
                    try:
                        await hyperion.delete(doc_name)
                    except HyperionError as e:
                        logger.warning(f"Failed to delete {doc_name}: {e.message}")
        
        # Delete chunks from database
        self.db.table("chunk")\
            .delete()\
            .eq("source_id", str(source_id))\
            .execute()
        
        # Update source status
        self.db.table("source")\
            .update({
                "ingestion_status": IngestionStatus.PENDING.value,
                "chunk_count": 0,
                "hyperion_doc_name": None,
            })\
            .eq("id", str(source_id))\
            .execute()
        
        return True


# Convenience function
async def ingest_source(source_id: UUID, force: bool = False) -> dict:
    """Ingest a source (convenience function)."""
    service = IngestionService()
    return await service.ingest_source(source_id, force)

