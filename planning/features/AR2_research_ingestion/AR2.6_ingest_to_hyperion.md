# AR2.6: Ingest Papers to Hyperion RAG

**Status**: pending  
**Priority**: P0  
**Depends On**: AR2.4 (GROBID parsing), AR2.5 (chunking)  
**Blocks**: AR3.* (all synthesis features)  
**Estimated Hours**: 8

## Summary

Send parsed academic paper chunks to Hyperion/LightRAG for semantic indexing and retrieval.

## Acceptance Criteria

- [ ] Call Hyperion `ingest_knowledge` tool via MCP
- [ ] Include metadata: DOI, title, authors, section, page_number
- [ ] Store LightRAG chunk_id reference in Supabase
- [ ] Verify retrieval works after ingestion
- [ ] Handle ingestion errors gracefully
- [ ] Support batch ingestion of multiple papers

## Data Flow

```
Paper (Supabase) → Chunks (from AR2.5) → Hyperion MCP → LightRAG
                                                ↓
                                    chunk_id returned
                                                ↓
                                    Store chunk_id in Supabase
```

## API Design

### Endpoint

```
POST /api/projects/{project_id}/sources/{source_id}/ingest
```

### Request

```json
{
  "force": false  // Re-ingest even if already ingested
}
```

### Response

```json
{
  "status": "success",
  "source_id": "uuid",
  "chunks_ingested": 15,
  "lightrag_document_id": "doc-xxx"
}
```

## Implementation

### Hyperion Client

```python
from typing import Optional
import httpx
import logging

logger = logging.getLogger(__name__)

class HyperionClient:
    """Client for Hyperion MCP (LightRAG wrapper)."""
    
    def __init__(
        self,
        mcp_url: str,
        auth_token: str,
        timeout: float = 30.0
    ):
        self.mcp_url = mcp_url
        self.auth_token = auth_token
        self.timeout = timeout
        self._session_id: Optional[str] = None
    
    async def _initialize_session(self) -> str:
        """Initialize MCP session and return session ID."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.mcp_url,
                headers={
                    "Authorization": f"Bearer {self.auth_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "academic-tool", "version": "1.0"}
                    }
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            self._session_id = response.headers.get("mcp-session-id")
            return self._session_id
    
    async def ingest_knowledge(
        self,
        texts: list[str],
        document_name: str
    ) -> dict:
        """Ingest text chunks to LightRAG."""
        if not self._session_id:
            await self._initialize_session()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.mcp_url,
                headers={
                    "Authorization": f"Bearer {self.auth_token}",
                    "Content-Type": "application/json",
                    "mcp-session-id": self._session_id
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "ingest_knowledge",
                        "arguments": {
                            "texts": texts,
                            "documentName": [document_name]
                        }
                    }
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
```

### Ingestion Service

```python
from uuid import UUID
from pydantic import BaseModel
from typing import Optional
import logging

from .hyperion_client import HyperionClient
from .database import get_chunks_for_source, update_chunk_lightrag_id

logger = logging.getLogger(__name__)

class IngestResult(BaseModel):
    source_id: UUID
    chunks_ingested: int
    lightrag_document_id: str
    errors: list[str] = []

async def ingest_source_to_hyperion(
    source_id: UUID,
    hyperion: HyperionClient,
    force: bool = False
) -> IngestResult:
    """Ingest all chunks from a source into Hyperion/LightRAG."""
    
    # Get chunks from Supabase
    chunks = await get_chunks_for_source(source_id)
    
    if not chunks:
        raise ValueError(f"No chunks found for source {source_id}")
    
    # Skip if already ingested (unless force)
    if not force and all(c.lightrag_id for c in chunks):
        logger.info(f"Source {source_id} already ingested, skipping")
        return IngestResult(
            source_id=source_id,
            chunks_ingested=0,
            lightrag_document_id=chunks[0].lightrag_id
        )
    
    # Prepare texts with metadata in content
    texts = []
    for chunk in chunks:
        # Include metadata in chunk text for LightRAG indexing
        text_with_metadata = f"""
[SECTION: {chunk.section_type}]
[PAGE: {chunk.page_number}]
{chunk.content}
"""
        texts.append(text_with_metadata.strip())
    
    # Get source metadata for document name
    source = await get_source(source_id)
    document_name = f"{source.doi}|{source.title[:50]}"
    
    # Ingest to Hyperion
    try:
        result = await hyperion.ingest_knowledge(
            texts=texts,
            document_name=document_name
        )
        
        # Extract document ID from response
        lightrag_doc_id = result.get("document_id", "unknown")
        
        # Update chunks with LightRAG reference
        for chunk in chunks:
            await update_chunk_lightrag_id(chunk.id, lightrag_doc_id)
        
        logger.info(f"Ingested {len(chunks)} chunks for source {source_id}")
        
        return IngestResult(
            source_id=source_id,
            chunks_ingested=len(chunks),
            lightrag_document_id=lightrag_doc_id
        )
        
    except Exception as e:
        logger.error(f"Failed to ingest source {source_id}: {e}")
        raise
```

## Database Schema

### Chunk Table Updates

```sql
-- Add LightRAG reference to chunks table
ALTER TABLE chunk 
ADD COLUMN lightrag_id TEXT,
ADD COLUMN ingested_at TIMESTAMPTZ;

-- Index for finding chunks by LightRAG ID
CREATE INDEX idx_chunk_lightrag_id ON chunk(lightrag_id);
```

## Error Handling

| Error | Action |
|-------|--------|
| Hyperion connection failed | Retry with exponential backoff |
| Auth error | Log and fail immediately |
| Chunk too large | Split and retry |
| Partial failure | Track which chunks failed |

## Testing

```python
@pytest.mark.asyncio
async def test_ingest_source_creates_lightrag_refs():
    """Test that ingestion creates LightRAG references."""
    source_id = create_test_source_with_chunks()
    
    result = await ingest_source_to_hyperion(source_id, hyperion_client)
    
    assert result.chunks_ingested > 0
    assert result.lightrag_document_id is not None
    
    # Verify chunks have lightrag_id
    chunks = await get_chunks_for_source(source_id)
    for chunk in chunks:
        assert chunk.lightrag_id is not None
```

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/services/hyperion_client.py` | Create |
| `src/services/ingestion.py` | Add ingest_source_to_hyperion |
| `src/api/routes/sources.py` | Add POST /{id}/ingest endpoint |
| `src/models/chunk.py` | Add lightrag_id field |

## Notes

- LightRAG document names include DOI for traceability
- Metadata is embedded in text since LightRAG metadata support is unknown
- Consider batching if large papers have many chunks

