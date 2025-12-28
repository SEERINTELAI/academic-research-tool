"""
Academic Paper Chunker.

Chunks parsed papers into segments suitable for RAG:
- Section-aware chunking
- Metadata embedding for provenance
- Token-based size limits with overlap
"""

import logging
import re
from typing import Optional
from uuid import UUID, uuid4

from src.models.chunk import (
    ChunkCreate,
    ChunkForIngestion,
    ChunkMetadata,
    ChunkerConfig,
    ChunkType,
)
from src.services.grobid_client import ParsedPaper, Section, SectionType

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.
    
    Uses simple heuristic: ~4 chars per token.
    For production, use tiktoken for exact counts.
    """
    return len(text) // 4


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    # Simple sentence splitter - handles common cases
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


class Chunker:
    """
    Chunks academic papers for RAG ingestion.
    
    Strategy:
    1. Split by sections (from GROBID)
    2. Within large sections, split by paragraphs
    3. Within large paragraphs, split by sentences with overlap
    4. Embed metadata in chunk text for retrieval context
    
    Usage:
        chunker = Chunker()
        chunks = chunker.chunk_paper(source_id, parsed_paper)
    """
    
    def __init__(self, config: Optional[ChunkerConfig] = None):
        """
        Initialize chunker.
        
        Args:
            config: Chunking configuration.
        """
        self.config = config or ChunkerConfig()
    
    def chunk_paper(
        self,
        source_id: UUID,
        paper: ParsedPaper,
        source_metadata: Optional[dict] = None,
    ) -> list[ChunkForIngestion]:
        """
        Chunk a parsed paper into RAG-ready segments.
        
        Args:
            source_id: Source ID in database.
            paper: Parsed paper from GROBID.
            source_metadata: Additional metadata (DOI, authors, etc.)
        
        Returns:
            List of chunks ready for ingestion.
        """
        source_metadata = source_metadata or {}
        chunks: list[ChunkForIngestion] = []
        
        # Extract base metadata
        base_metadata = ChunkMetadata(
            source_id=source_id,
            doi=source_metadata.get("doi"),
            arxiv_id=source_metadata.get("arxiv_id"),
            authors=[a.full_name for a in paper.authors],
            publication_year=source_metadata.get("publication_year"),
            title=paper.title or source_metadata.get("title"),
        )
        
        # Chunk abstract
        if paper.abstract:
            abstract_chunk = self._create_chunk(
                content=paper.abstract,
                chunk_type=ChunkType.ABSTRACT,
                section_type="abstract",
                section_title="Abstract",
                base_metadata=base_metadata,
                chunk_index=len(chunks),
            )
            chunks.append(abstract_chunk)
        
        # Chunk sections
        for section in paper.sections:
            section_chunks = self._chunk_section(
                section=section,
                base_metadata=base_metadata,
                start_index=len(chunks),
            )
            chunks.extend(section_chunks)
        
        # Update total_chunks in all metadata
        total = len(chunks)
        for chunk in chunks:
            chunk.metadata.total_chunks = total
        
        logger.info(f"Created {len(chunks)} chunks from paper '{paper.title}'")
        return chunks
    
    def _chunk_section(
        self,
        section: Section,
        base_metadata: ChunkMetadata,
        start_index: int,
    ) -> list[ChunkForIngestion]:
        """Chunk a single section."""
        chunks: list[ChunkForIngestion] = []
        
        if not section.text.strip():
            return chunks
        
        text_tokens = estimate_tokens(section.text)
        
        if text_tokens <= self.config.max_chunk_tokens:
            # Section fits in one chunk
            chunk = self._create_chunk(
                content=section.text,
                chunk_type=ChunkType.SECTION,
                section_type=section.section_type.value,
                section_title=section.title,
                base_metadata=base_metadata,
                chunk_index=start_index + len(chunks),
                page_start=section.page_start,
                page_end=section.page_end,
            )
            chunks.append(chunk)
        else:
            # Split section into smaller chunks
            sub_chunks = self._split_text(
                text=section.text,
                section_type=section.section_type.value,
                section_title=section.title,
                base_metadata=base_metadata,
                start_index=start_index,
                page_start=section.page_start,
            )
            chunks.extend(sub_chunks)
        
        # Recursively handle subsections
        for subsection in section.subsections:
            sub_chunks = self._chunk_section(
                section=subsection,
                base_metadata=base_metadata,
                start_index=start_index + len(chunks),
            )
            chunks.extend(sub_chunks)
        
        return chunks
    
    def _split_text(
        self,
        text: str,
        section_type: str,
        section_title: Optional[str],
        base_metadata: ChunkMetadata,
        start_index: int,
        page_start: Optional[int] = None,
    ) -> list[ChunkForIngestion]:
        """Split large text into token-limited chunks with overlap."""
        chunks: list[ChunkForIngestion] = []
        
        # First try splitting by paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        
        current_chunk_text = ""
        current_chunk_tokens = 0
        
        for para in paragraphs:
            para_tokens = estimate_tokens(para)
            
            if para_tokens > self.config.max_chunk_tokens:
                # Paragraph too large - split by sentences
                if current_chunk_text:
                    # Save current chunk first
                    chunk = self._create_chunk(
                        content=current_chunk_text,
                        chunk_type=ChunkType.PARAGRAPH,
                        section_type=section_type,
                        section_title=section_title,
                        base_metadata=base_metadata,
                        chunk_index=start_index + len(chunks),
                        page_start=page_start,
                    )
                    chunks.append(chunk)
                    current_chunk_text = ""
                    current_chunk_tokens = 0
                
                # Split large paragraph by sentences
                sentence_chunks = self._split_by_sentences(
                    text=para,
                    section_type=section_type,
                    section_title=section_title,
                    base_metadata=base_metadata,
                    start_index=start_index + len(chunks),
                    page_start=page_start,
                )
                chunks.extend(sentence_chunks)
                
            elif current_chunk_tokens + para_tokens > self.config.max_chunk_tokens:
                # Would exceed limit - save current and start new
                if current_chunk_text:
                    chunk = self._create_chunk(
                        content=current_chunk_text,
                        chunk_type=ChunkType.PARAGRAPH,
                        section_type=section_type,
                        section_title=section_title,
                        base_metadata=base_metadata,
                        chunk_index=start_index + len(chunks),
                        page_start=page_start,
                    )
                    chunks.append(chunk)
                
                # Start new chunk (with overlap if configured)
                if self.config.overlap_tokens > 0 and current_chunk_text:
                    overlap = self._get_overlap_text(current_chunk_text)
                    current_chunk_text = overlap + "\n\n" + para
                else:
                    current_chunk_text = para
                current_chunk_tokens = estimate_tokens(current_chunk_text)
            else:
                # Add to current chunk
                if current_chunk_text:
                    current_chunk_text += "\n\n" + para
                else:
                    current_chunk_text = para
                current_chunk_tokens += para_tokens
        
        # Save final chunk
        if current_chunk_text and current_chunk_tokens >= self.config.min_chunk_tokens:
            chunk = self._create_chunk(
                content=current_chunk_text,
                chunk_type=ChunkType.PARAGRAPH,
                section_type=section_type,
                section_title=section_title,
                base_metadata=base_metadata,
                chunk_index=start_index + len(chunks),
                page_start=page_start,
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_by_sentences(
        self,
        text: str,
        section_type: str,
        section_title: Optional[str],
        base_metadata: ChunkMetadata,
        start_index: int,
        page_start: Optional[int] = None,
    ) -> list[ChunkForIngestion]:
        """Split text by sentences when paragraphs are too large."""
        chunks: list[ChunkForIngestion] = []
        sentences = split_into_sentences(text)
        
        current_chunk_sentences: list[str] = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = estimate_tokens(sentence)
            
            if current_tokens + sentence_tokens > self.config.max_chunk_tokens:
                # Save current chunk
                if current_chunk_sentences:
                    chunk_text = " ".join(current_chunk_sentences)
                    if estimate_tokens(chunk_text) >= self.config.min_chunk_tokens:
                        chunk = self._create_chunk(
                            content=chunk_text,
                            chunk_type=ChunkType.PARAGRAPH,
                            section_type=section_type,
                            section_title=section_title,
                            base_metadata=base_metadata,
                            chunk_index=start_index + len(chunks),
                            page_start=page_start,
                        )
                        chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(current_chunk_sentences)
                current_chunk_sentences = overlap_sentences + [sentence]
                current_tokens = sum(estimate_tokens(s) for s in current_chunk_sentences)
            else:
                current_chunk_sentences.append(sentence)
                current_tokens += sentence_tokens
        
        # Save final chunk
        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences)
            if estimate_tokens(chunk_text) >= self.config.min_chunk_tokens:
                chunk = self._create_chunk(
                    content=chunk_text,
                    chunk_type=ChunkType.PARAGRAPH,
                    section_type=section_type,
                    section_title=section_title,
                    base_metadata=base_metadata,
                    chunk_index=start_index + len(chunks),
                    page_start=page_start,
                )
                chunks.append(chunk)
        
        return chunks
    
    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from end of chunk."""
        target_tokens = self.config.overlap_tokens
        
        # Take from end of text
        words = text.split()
        overlap_words = []
        current_tokens = 0
        
        for word in reversed(words):
            word_tokens = estimate_tokens(word)
            if current_tokens + word_tokens > target_tokens:
                break
            overlap_words.insert(0, word)
            current_tokens += word_tokens
        
        return " ".join(overlap_words)
    
    def _get_overlap_sentences(self, sentences: list[str]) -> list[str]:
        """Get overlap sentences from end of chunk."""
        target_tokens = self.config.overlap_tokens
        overlap = []
        current_tokens = 0
        
        for sentence in reversed(sentences):
            sentence_tokens = estimate_tokens(sentence)
            if current_tokens + sentence_tokens > target_tokens:
                break
            overlap.insert(0, sentence)
            current_tokens += sentence_tokens
        
        return overlap
    
    def _create_chunk(
        self,
        content: str,
        chunk_type: ChunkType,
        section_type: str,
        section_title: Optional[str],
        base_metadata: ChunkMetadata,
        chunk_index: int,
        page_start: Optional[int] = None,
        page_end: Optional[int] = None,
    ) -> ChunkForIngestion:
        """Create a chunk with metadata."""
        chunk_id = uuid4()
        
        # Build metadata for this chunk
        metadata = ChunkMetadata(
            source_id=base_metadata.source_id,
            doi=base_metadata.doi,
            arxiv_id=base_metadata.arxiv_id,
            section_type=section_type,
            section_title=section_title,
            page_start=page_start,
            page_end=page_end,
            chunk_index=chunk_index,
            total_chunks=0,  # Updated later
            authors=base_metadata.authors,
            publication_year=base_metadata.publication_year,
            title=base_metadata.title,
        )
        
        # Build text with embedded metadata
        if self.config.embed_metadata_in_text:
            prefix = self._build_metadata_prefix(metadata)
            text_with_metadata = prefix + content
        else:
            text_with_metadata = content
        
        # Build doc_name for Hyperion
        doc_name = self._build_doc_name(metadata, chunk_index)
        
        return ChunkForIngestion(
            id=chunk_id,
            text=text_with_metadata,
            doc_name=doc_name,
            raw_content=content,
            metadata=metadata,
        )
    
    def _build_metadata_prefix(self, metadata: ChunkMetadata) -> str:
        """Build metadata prefix for chunk text."""
        parts = []
        
        if metadata.title:
            parts.append(f"Source: {metadata.title}")
        
        if metadata.authors:
            author_str = ", ".join(metadata.authors[:3])
            if len(metadata.authors) > 3:
                author_str += " et al."
            parts.append(f"Authors: {author_str}")
        
        if metadata.publication_year:
            parts.append(f"Year: {metadata.publication_year}")
        
        if metadata.section_title:
            parts.append(f"Section: {metadata.section_title}")
        elif metadata.section_type:
            parts.append(f"Section: {metadata.section_type}")
        
        if metadata.page_start:
            if metadata.page_end and metadata.page_end != metadata.page_start:
                parts.append(f"Pages: {metadata.page_start}-{metadata.page_end}")
            else:
                parts.append(f"Page: {metadata.page_start}")
        
        if not parts:
            return ""
        
        return "[" + " | ".join(parts) + "]\n\n"
    
    def _build_doc_name(self, metadata: ChunkMetadata, chunk_index: int) -> str:
        """Build document name for Hyperion."""
        # Format: source_id:chunk_index:section_type
        parts = [
            str(metadata.source_id)[:8],  # First 8 chars of UUID
            f"c{chunk_index:03d}",
            metadata.section_type or "unknown",
        ]
        return "_".join(parts)


# Convenience function
def chunk_paper(
    source_id: UUID,
    paper: ParsedPaper,
    source_metadata: Optional[dict] = None,
    config: Optional[ChunkerConfig] = None,
) -> list[ChunkForIngestion]:
    """Chunk a paper (convenience function)."""
    chunker = Chunker(config)
    return chunker.chunk_paper(source_id, paper, source_metadata)

