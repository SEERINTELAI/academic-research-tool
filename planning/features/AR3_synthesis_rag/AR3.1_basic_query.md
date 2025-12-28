# AR3.1: Basic Query Interface

**Status**: pending  
**Priority**: P0  
**Depends On**: AR2.6 (ingestion working)  
**Blocks**: AR3.2, AR3.3, AR4.2, AR5.1  
**Estimated Hours**: 10

## Summary

Query ingested papers via Hyperion/LightRAG and return cited answers with source attribution.

## Acceptance Criteria

- [ ] Accept natural language query
- [ ] Query Hyperion for relevant chunks
- [ ] Synthesize answer using Claude
- [ ] Include source citations in response
- [ ] Store synthesis record for provenance
- [ ] Support filtering by specific sources

## Data Flow

```
User Query
     ↓
Enhance query (Claude)
     ↓
Query Hyperion (LightRAG)
     ↓
Retrieve relevant chunks
     ↓
Synthesize answer (Claude)
     ↓
Format with citations
     ↓
Store synthesis record
     ↓
Return to user
```

## API Design

### Query Papers

```
POST /api/projects/{project_id}/research/query
```

Request:
```json
{
  "query": "What methods are commonly used for sentiment analysis?",
  "source_ids": ["uuid1", "uuid2"],  // Optional filter
  "max_sources": 5  // Max sources to retrieve
}
```

Response:
```json
{
  "synthesis_id": "uuid",
  "query": "What methods are commonly used for sentiment analysis?",
  "response": "Several methods are commonly used for sentiment analysis. Smith et al. (2024) found that transformer-based approaches achieve the highest accuracy, while Jones (2023) demonstrated that ensemble methods provide more robust results...",
  "sources": [
    {
      "chunk_id": "uuid",
      "source_id": "uuid",
      "source_title": "Deep Learning for Sentiment Analysis",
      "authors": ["Smith, J.", "Doe, A."],
      "year": 2024,
      "section": "results",
      "page": 8,
      "score": 0.94,
      "excerpt": "Our transformer-based approach achieved 95% accuracy..."
    },
    {
      "chunk_id": "uuid",
      "source_id": "uuid",
      "source_title": "Ensemble Methods in NLP",
      "authors": ["Jones, M."],
      "year": 2023,
      "section": "methodology",
      "page": 5,
      "score": 0.89,
      "excerpt": "Ensemble methods combining multiple classifiers..."
    }
  ]
}
```

## Implementation

### Query Service

```python
from uuid import UUID
from typing import Optional
import logging

from .hyperion_client import HyperionClient
from .claude_client import ClaudeClient
from .database import (
    get_source,
    get_chunks_by_lightrag_ids,
    create_synthesis
)

logger = logging.getLogger(__name__)

class QueryService:
    def __init__(
        self,
        hyperion: HyperionClient,
        claude: ClaudeClient
    ):
        self.hyperion = hyperion
        self.claude = claude
    
    async def query_papers(
        self,
        project_id: UUID,
        query: str,
        source_ids: Optional[list[UUID]] = None,
        max_sources: int = 5
    ) -> dict:
        """Query ingested papers and synthesize answer."""
        
        # Step 1: Enhance query
        enhanced_query = await self._enhance_query(query)
        
        # Step 2: Query Hyperion
        hyperion_response = await self.hyperion.query_knowledge(
            query=enhanced_query,
            mode="hybrid"  # Use hybrid search for best results
        )
        
        # Step 3: Parse chunks from response
        chunks = await self._parse_hyperion_response(
            hyperion_response,
            source_ids,
            max_sources
        )
        
        # Step 4: Synthesize answer
        answer = await self._synthesize_answer(query, chunks)
        
        # Step 5: Store synthesis record
        synthesis_id = await create_synthesis(
            project_id=project_id,
            query=query,
            enhanced_query=enhanced_query,
            response=answer,
            chunk_ids=[c["chunk_id"] for c in chunks],
            scores=[c["score"] for c in chunks]
        )
        
        return {
            "synthesis_id": synthesis_id,
            "query": query,
            "response": answer,
            "sources": chunks
        }
    
    async def _enhance_query(self, query: str) -> str:
        """Use Claude to enhance query for better retrieval."""
        prompt = f"""Enhance this academic research query for better retrieval.
Keep the core meaning but expand with synonyms and related terms.

Original query: {query}

Enhanced query (single line):"""
        
        response = await self.claude.complete(prompt, max_tokens=100)
        return response.strip()
    
    async def _parse_hyperion_response(
        self,
        response: dict,
        source_filter: Optional[list[UUID]],
        max_sources: int
    ) -> list[dict]:
        """Parse Hyperion response into structured chunk data."""
        
        chunks = []
        for source in response.get("sources", [])[:max_sources]:
            chunk_data = await self._get_chunk_metadata(source)
            
            # Apply source filter if provided
            if source_filter and chunk_data["source_id"] not in source_filter:
                continue
            
            chunks.append(chunk_data)
        
        return chunks
    
    async def _get_chunk_metadata(self, source: dict) -> dict:
        """Get full metadata for a retrieved chunk."""
        # Look up chunk in Supabase by LightRAG ID
        chunk = await get_chunks_by_lightrag_ids([source["id"]])
        if not chunk:
            return {
                "chunk_id": None,
                "source_id": None,
                "excerpt": source.get("content", ""),
                "score": source.get("score", 0)
            }
        
        chunk = chunk[0]
        source_data = await get_source(chunk.source_id)
        
        return {
            "chunk_id": chunk.id,
            "source_id": chunk.source_id,
            "source_title": source_data.title,
            "authors": source_data.authors,
            "year": source_data.publication_date.year,
            "section": chunk.section_type,
            "page": chunk.page_number,
            "score": source.get("score", 0),
            "excerpt": chunk.content[:300]
        }
    
    async def _synthesize_answer(
        self,
        query: str,
        chunks: list[dict]
    ) -> str:
        """Use Claude to synthesize answer from chunks."""
        
        # Format chunks for prompt
        sources_text = "\n\n".join([
            f"[{i+1}] {c['source_title']} ({c['authors'][0] if c.get('authors') else 'Unknown'}, {c.get('year', 'n.d.')})\n"
            f"Section: {c.get('section', 'unknown')}, Page: {c.get('page', 'n/a')}\n"
            f"Content: {c['excerpt']}"
            for i, c in enumerate(chunks)
        ])
        
        prompt = f"""Based on the following academic sources, answer the research question.
Include in-text citations in (Author, Year) format.

RESEARCH QUESTION: {query}

SOURCES:
{sources_text}

ANSWER (with citations):"""
        
        response = await self.claude.complete(prompt, max_tokens=1000)
        return response.strip()
```

### API Route

```python
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

from ..models.research import QueryRequest, QueryResponse
from ..services.query import QueryService
from ..services.auth import get_current_user

router = APIRouter(prefix="/api/projects/{project_id}/research", tags=["research"])

@router.post("/query", response_model=QueryResponse)
async def query_papers(
    project_id: UUID,
    request: QueryRequest,
    user_id: UUID = Depends(get_current_user),
    query_service: QueryService = Depends()
):
    """Query ingested papers and get synthesized answer."""
    
    # Verify project access
    await verify_project_access(project_id, user_id)
    
    result = await query_service.query_papers(
        project_id=project_id,
        query=request.query,
        source_ids=request.source_ids,
        max_sources=request.max_sources
    )
    
    return result
```

## Testing

```python
@pytest.mark.asyncio
async def test_query_returns_cited_answer():
    """Test that query returns answer with citations."""
    # Setup: create project with ingested sources
    project_id = await create_project_with_sources()
    
    response = await client.post(
        f"/api/projects/{project_id}/research/query",
        json={"query": "What are the main findings?"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Has synthesis ID for provenance
    assert data["synthesis_id"] is not None
    
    # Has cited answer
    assert len(data["response"]) > 0
    assert "(" in data["response"]  # Contains citations
    
    # Has source details
    assert len(data["sources"]) > 0
    for source in data["sources"]:
        assert source["chunk_id"] is not None
        assert source["page"] is not None

@pytest.mark.asyncio
async def test_query_respects_source_filter():
    """Test that query filters by specified sources."""
    project_id = await create_project_with_sources()
    source_ids = [await get_first_source_id(project_id)]
    
    response = await client.post(
        f"/api/projects/{project_id}/research/query",
        json={
            "query": "What methods were used?",
            "source_ids": source_ids
        },
        headers=auth_headers
    )
    
    data = response.json()
    for source in data["sources"]:
        assert source["source_id"] in source_ids
```

## Files to Create

| File | Action |
|------|--------|
| `src/services/query.py` | Create |
| `src/services/claude_client.py` | Create |
| `src/models/research.py` | Create |
| `src/api/routes/research.py` | Create |

## Notes

- Query enhancement improves retrieval quality
- Claude prompt engineering is critical for good synthesis
- Consider caching common queries
- Hybrid search mode recommended for academic content

