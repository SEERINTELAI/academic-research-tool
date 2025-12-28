# Academic Research Tool - Master Plan

**Project**: AI-powered academic paper writing assistant  
**Status**: Phase 1 - Planning  
**Last Updated**: 2025-12-28

## Vision

Create a "Cursor for academic paper writing" - a tight loop between outlining, researching, synthesizing sources, and collaborative report writing.

## MVP Scope

### Included in MVP
- Single-user projects
- PDF ingestion via GROBID
- RAG queries via Hyperion/LightRAG
- Basic writing editor with AI assist
- In-text citations with bibliography
- Semantic Scholar + arXiv search

### Deferred Post-MVP
- Multi-user collaboration
- Real-time sync
- Reference manager import
- LaTeX export
- Multi-language support

---

## Feature Categories

### AR1: Outline Formation (4 features)

Collaborative research outline structuring with AI assistance.

| ID | Feature | Status | Priority |
|----|---------|--------|----------|
| AR1.1 | Create Project with Outline | 🔜 pending | P0 |
| AR1.2 | AI-Assisted Section Generation | 🔜 pending | P1 |
| AR1.3 | Research Question Formulation | 🔜 pending | P1 |
| AR1.4 | Outline-to-Structure Conversion | 🔜 pending | P2 |

**Wave**: 2a  
**Dependencies**: None  
**See**: [features/AR1_outline_formation/](features/AR1_outline_formation/)

---

### AR2: Research & Ingestion (6 features)

Academic paper search, retrieval, and PDF parsing.

| ID | Feature | Status | Priority |
|----|---------|--------|----------|
| AR2.1 | Paper Search (Semantic Scholar) | 🔜 pending | P0 |
| AR2.2 | Paper Search (OpenAlex) | 🔜 pending | P1 |
| AR2.3 | Paper Search (arXiv) | 🔜 pending | P1 |
| AR2.4 | PDF Download & GROBID Parsing | 🔜 pending | P0 |
| AR2.5 | Chunk by Section | 🔜 pending | P0 |
| AR2.6 | Ingest to Hyperion RAG | 🔜 pending | P0 |

**Wave**: 2b  
**Dependencies**: Hyperion validation  
**See**: [features/AR2_research_ingestion/](features/AR2_research_ingestion/)

---

### AR3: Synthesis (RAG) (5 features)

Query papers via Hyperion, get cited answers.

| ID | Feature | Status | Priority |
|----|---------|--------|----------|
| AR3.1 | Basic Query Interface | 🔜 pending | P0 |
| AR3.2 | Multi-Paper Query | 🔜 pending | P0 |
| AR3.3 | Compare Findings | 🔜 pending | P1 |
| AR3.4 | Summarize Paper | 🔜 pending | P1 |
| AR3.5 | Query with Context | 🔜 pending | P2 |

**Wave**: 2c  
**Dependencies**: AR2.6 (ingestion working)  
**See**: [features/AR3_synthesis_rag/](features/AR3_synthesis_rag/)

---

### AR4: Report Writing (5 features)

Collaborative editor with AI assistance.

| ID | Feature | Status | Priority |
|----|---------|--------|----------|
| AR4.1 | Basic Editor (Monaco) | 🔜 pending | P0 |
| AR4.2 | AI Writing Assist | 🔜 pending | P0 |
| AR4.3 | Auto-Insert Citations | 🔜 pending | P0 |
| AR4.4 | Section-Aware Suggestions | 🔜 pending | P1 |
| AR4.5 | Draft Versioning | 🔜 pending | P2 |

**Wave**: 3a  
**Dependencies**: AR3.1 (query working)  
**See**: [features/AR4_report_writing/](features/AR4_report_writing/)

---

### AR5: Citation Management (4 features)

Citation provenance, formatting, and export.

| ID | Feature | Status | Priority |
|----|---------|--------|----------|
| AR5.1 | Citation Provenance Tracking | 🔜 pending | P0 |
| AR5.2 | In-Text Citation Formatting | 🔜 pending | P0 |
| AR5.3 | Bibliography Generation | 🔜 pending | P0 |
| AR5.4 | Citation Style Switching | 🔜 pending | P1 |

**Wave**: 3b  
**Dependencies**: AR3.1, AR4.3  
**See**: [features/AR5_citation_management/](features/AR5_citation_management/)

---

## Build Order

```
Wave 0: Pre-requisites ✅
├── AK RAG Inventory ✅
├── Hyperion Documentation ✅
├── RAG Test Suite ✅
└── Decision Gate ✅

Wave 1: Foundation (Current)
├── Create Repository ⏳
├── Planning Infrastructure ⏳
├── tasks.json ⏳
└── Validate Hyperion with credentials

Wave 2: Core Pipeline
├── 2a: Outline (AR1.1, AR1.2)
├── 2b: Ingestion (AR2.1, AR2.4, AR2.5, AR2.6)
└── 2c: Synthesis (AR3.1, AR3.2)

Wave 3: Writing & Citations
├── 3a: Editor (AR4.1, AR4.2, AR4.3)
└── 3b: Citations (AR5.1, AR5.2, AR5.3)

Wave 4: Polish
├── Additional search sources
├── Advanced features
└── UX refinement
```

---

## Priority Legend

| Priority | Meaning | Include in MVP |
|----------|---------|----------------|
| P0 | Must have for MVP | Yes |
| P1 | Should have for MVP | If time |
| P2 | Nice to have | Post-MVP |

---

## Technical Notes

### RAG Layer

- **Backend**: Hyperion MCP → LightRAG
- **Endpoint**: `https://n8n-dev-u36296.vm.elestio.app/mcp/hyperion`
- **Status**: Validated (see [AK_RAG_DECISION_GATE.md](../../planning/AK_RAG_DECISION_GATE.md))
- **Note**: Hyperion is separate from AK - call directly

### External APIs

| API | Purpose | Rate Limit | Auth Required |
|-----|---------|------------|---------------|
| Semantic Scholar | Paper search | 100/5min | Optional |
| OpenAlex | Paper search | Unlimited | No |
| arXiv | Paper search & PDF | Unlimited | No |
| GROBID | PDF parsing | Self-hosted | No |
| Claude | LLM | Per plan | Yes |

### Database Schema

See [ARCHITECTURE.md](../ARCHITECTURE.md) for full schema.

Key tables:
- `project` - Research project container
- `outline` - Section structure
- `source` - Ingested papers
- `chunk` - Indexed text chunks
- `synthesis` - Query responses
- `citation` - In-document references
- `report` - Written document

---

## Metrics

### MVP Success Criteria

1. User can search and ingest 5 papers in < 10 minutes
2. RAG query returns relevant chunks with citations
3. User can write a 1000-word section with AI assist
4. Bibliography auto-generates from used citations
5. End-to-end demo: outline → research → write → cite

### Performance Targets

| Metric | Target |
|--------|--------|
| Paper ingestion | < 30s per paper |
| RAG query | < 5s response |
| Citation generation | < 1s |
| Page load | < 2s |

---

## Related Documents

- [Architecture](../ARCHITECTURE.md)
- [Planning README](README.md)
- [Tasks](tasks.json)
- [AK RAG Validation](../../planning/AK_RAG_DECISION_GATE.md)

