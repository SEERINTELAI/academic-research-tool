# AR5.1: Citation Provenance Tracking

**Status**: pending  
**Priority**: P0  
**Depends On**: AR2.6 (ingestion), AR3.1 (query)  
**Blocks**: AR4.3 (auto-citations)  
**Estimated Hours**: 12

## Summary

Track the complete provenance chain from source PDF through RAG retrieval to final citation in the user's document.

## Acceptance Criteria

- [ ] Store provenance for every synthesis (query response)
- [ ] Link citations to specific chunks with page numbers
- [ ] Support tracing any citation back to source PDF
- [ ] Provide API to verify citation accuracy
- [ ] Handle multi-source syntheses correctly

## Provenance Chain

```
Source PDF
     ↓
GROBID Extraction
     ↓
Chunk (with section, page)
     ↓
LightRAG Storage (chunk_id)
     ↓
Query Retrieval (synthesis)
     ↓
User Inserts Citation
     ↓
Citation Record (linked to chunk + synthesis)
```

## Data Model

### Synthesis Table

```sql
CREATE TABLE synthesis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES project(id),
    query TEXT NOT NULL,
    enhanced_query TEXT,  -- Query after LLM enhancement
    response TEXT NOT NULL,
    
    -- Provenance
    chunk_ids UUID[],  -- All chunks used
    scores FLOAT[],  -- Relevance scores per chunk
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_synthesis_project ON synthesis(project_id);
CREATE INDEX idx_synthesis_chunks ON synthesis USING GIN(chunk_ids);
```

### Citation Provenance Table

```sql
CREATE TABLE citation_provenance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Links
    report_id UUID REFERENCES report(id),
    synthesis_id UUID REFERENCES synthesis(id),
    chunk_id UUID REFERENCES chunk(id),
    source_id UUID REFERENCES source(id),
    
    -- Citation details
    in_text_citation TEXT NOT NULL,  -- e.g., "(Smith, 2024)"
    quote_text TEXT,  -- Exact quote if applicable
    page_number INT,
    section_in_paper TEXT,
    
    -- Position in user's document
    position_in_report JSONB,  -- {section: 1, paragraph: 3, offset: 150}
    
    -- Verification
    verified BOOLEAN DEFAULT FALSE,
    match_score FLOAT,  -- How well citation matches source
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_citation_report ON citation_provenance(report_id);
CREATE INDEX idx_citation_synthesis ON citation_provenance(synthesis_id);
CREATE INDEX idx_citation_source ON citation_provenance(source_id);
```

## API Design

### Create Synthesis (with provenance)

```
POST /api/projects/{project_id}/research/query
```

Request:
```json
{
  "query": "What methods do papers use for X?",
  "source_ids": ["uuid1", "uuid2"]  // Optional filter
}
```

Response:
```json
{
  "synthesis_id": "uuid",
  "query": "What methods do papers use for X?",
  "response": "Studies use various methods for X. Smith (2024) found...",
  "sources": [
    {
      "chunk_id": "uuid",
      "source_id": "uuid",
      "source_title": "Paper Title",
      "section": "methods",
      "page": 5,
      "score": 0.92,
      "excerpt": "...relevant excerpt..."
    }
  ]
}
```

### Create Citation (link to synthesis)

```
POST /api/reports/{report_id}/citations
```

Request:
```json
{
  "synthesis_id": "uuid",
  "chunk_id": "uuid",
  "in_text_citation": "(Smith, 2024)",
  "position_in_report": {"section": 2, "paragraph": 3, "offset": 150},
  "quote_text": "optional exact quote"
}
```

### Get Citation Provenance

```
GET /api/citations/{citation_id}/provenance
```

Response:
```json
{
  "citation_id": "uuid",
  "in_text": "(Smith, 2024, p. 5)",
  "chain": {
    "citation": {
      "id": "uuid",
      "position": {"section": 2, "paragraph": 3}
    },
    "synthesis": {
      "id": "uuid",
      "query": "What methods...",
      "response_excerpt": "Smith (2024) found..."
    },
    "chunk": {
      "id": "uuid",
      "content": "Full chunk text...",
      "section": "methods",
      "page": 5
    },
    "source": {
      "id": "uuid",
      "doi": "10.1234/test.2024.001",
      "title": "Paper Title",
      "authors": ["Smith, J.", "Jones, M."],
      "publication_date": "2024-01-15"
    }
  }
}
```

### Verify Citation

```
POST /api/citations/{citation_id}/verify
```

Response:
```json
{
  "verified": true,
  "match_score": 0.87,
  "issues": [],
  "source_quote": "exact text from source",
  "citation_claim": "what the citation claims"
}
```

## Implementation

### Pydantic Models

```python
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class ChunkSource(BaseModel):
    chunk_id: UUID
    source_id: UUID
    source_title: str
    section: str
    page: int
    score: float
    excerpt: str

class SynthesisCreate(BaseModel):
    query: str
    source_ids: Optional[list[UUID]] = None

class SynthesisResponse(BaseModel):
    synthesis_id: UUID
    query: str
    response: str
    sources: list[ChunkSource]

class CitationCreate(BaseModel):
    synthesis_id: UUID
    chunk_id: UUID
    in_text_citation: str
    position_in_report: dict
    quote_text: Optional[str] = None

class ProvenanceChain(BaseModel):
    citation_id: UUID
    in_text: str
    chain: dict

class VerificationResult(BaseModel):
    verified: bool
    match_score: float
    issues: list[str]
    source_quote: str
    citation_claim: str
```

### Provenance Service

```python
from uuid import UUID
from typing import Optional
import logging

from .database import (
    get_synthesis,
    get_chunk,
    get_source,
    get_citation,
    create_citation_provenance
)

logger = logging.getLogger(__name__)

async def create_citation_with_provenance(
    report_id: UUID,
    synthesis_id: UUID,
    chunk_id: UUID,
    in_text_citation: str,
    position: dict,
    quote_text: Optional[str] = None
) -> UUID:
    """Create a citation with full provenance tracking."""
    
    # Get related entities
    chunk = await get_chunk(chunk_id)
    source = await get_source(chunk.source_id)
    synthesis = await get_synthesis(synthesis_id)
    
    # Verify chunk was used in synthesis
    if chunk_id not in synthesis.chunk_ids:
        logger.warning(f"Chunk {chunk_id} not in synthesis {synthesis_id}")
    
    # Create provenance record
    citation_id = await create_citation_provenance(
        report_id=report_id,
        synthesis_id=synthesis_id,
        chunk_id=chunk_id,
        source_id=source.id,
        in_text_citation=in_text_citation,
        quote_text=quote_text,
        page_number=chunk.page_number,
        section_in_paper=chunk.section_type,
        position_in_report=position
    )
    
    logger.info(f"Created citation {citation_id} with provenance")
    return citation_id

async def get_full_provenance(citation_id: UUID) -> dict:
    """Get complete provenance chain for a citation."""
    
    citation = await get_citation(citation_id)
    synthesis = await get_synthesis(citation.synthesis_id)
    chunk = await get_chunk(citation.chunk_id)
    source = await get_source(citation.source_id)
    
    return {
        "citation_id": citation_id,
        "in_text": citation.in_text_citation,
        "chain": {
            "citation": {
                "id": str(citation.id),
                "position": citation.position_in_report
            },
            "synthesis": {
                "id": str(synthesis.id),
                "query": synthesis.query,
                "response_excerpt": synthesis.response[:200]
            },
            "chunk": {
                "id": str(chunk.id),
                "content": chunk.content,
                "section": chunk.section_type,
                "page": chunk.page_number
            },
            "source": {
                "id": str(source.id),
                "doi": source.doi,
                "title": source.title,
                "authors": source.authors,
                "publication_date": str(source.publication_date)
            }
        }
    }

async def verify_citation(citation_id: UUID) -> dict:
    """Verify citation accuracy against source."""
    
    citation = await get_citation(citation_id)
    chunk = await get_chunk(citation.chunk_id)
    synthesis = await get_synthesis(citation.synthesis_id)
    
    issues = []
    
    # Check if quote exists in source
    if citation.quote_text:
        if citation.quote_text not in chunk.content:
            issues.append("Quote not found in source chunk")
    
    # Calculate rough match score
    # (In production, use semantic similarity)
    match_score = 0.85  # Placeholder
    
    return {
        "verified": len(issues) == 0,
        "match_score": match_score,
        "issues": issues,
        "source_quote": chunk.content[:200],
        "citation_claim": synthesis.response[:200]
    }
```

## Testing

```python
@pytest.mark.asyncio
async def test_citation_provenance_complete():
    """Test that citation has complete provenance chain."""
    # Setup: create source, chunks, synthesis
    source_id = await create_test_source()
    chunk_id = await create_test_chunk(source_id)
    synthesis_id = await create_test_synthesis([chunk_id])
    
    # Create citation
    citation_id = await create_citation_with_provenance(
        report_id=uuid4(),
        synthesis_id=synthesis_id,
        chunk_id=chunk_id,
        in_text_citation="(Test, 2024)",
        position={"section": 1, "paragraph": 1}
    )
    
    # Get provenance
    provenance = await get_full_provenance(citation_id)
    
    # Verify chain is complete
    assert provenance["chain"]["source"]["id"] is not None
    assert provenance["chain"]["chunk"]["page"] is not None
    assert provenance["chain"]["synthesis"]["query"] is not None

@pytest.mark.asyncio
async def test_citation_verification_detects_mismatch():
    """Test that verification catches mismatched citations."""
    # Create citation with wrong quote
    citation_id = await create_citation_with_wrong_quote()
    
    result = await verify_citation(citation_id)
    
    assert not result["verified"]
    assert "Quote not found" in result["issues"][0]
```

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/models/synthesis.py` | Create |
| `src/models/citation.py` | Create |
| `src/services/provenance.py` | Create |
| `src/api/routes/research.py` | Add synthesis endpoints |
| `src/api/routes/citations.py` | Create |

## Notes

- Provenance is critical for academic credibility
- Consider caching provenance chains for frequently-cited sources
- Match score calculation should use semantic similarity in production
- Multi-source citations need special handling (multiple chunks)

