# Academic Research Tool

**AI-powered academic paper writing assistant** - Think "Cursor for academic paper writing."

## Overview

A tight loop between outlining, researching, synthesizing sources, and collaborative report writing.

### Core Features

1. **Outline Formation**: Collaborate with AI to structure research outline
2. **Research & Ingestion**: Search academic databases, retrieve papers, parse PDFs
3. **Synthesis (RAG)**: Query papers, get cited answers, compare findings
4. **Report Writing**: Collaborative editor with AI assistance and auto-citations
5. **Citation Management**: Track provenance, format citations, generate bibliography

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                      │
│  - Research Tab (Explore, Library, Tree, Outline + Chat)    │
│  - Write Tab (Monaco Editor with AI assist)                 │
└─────────────────────────────────────────────────────────────┘
                              │
                         REST API
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                        │
│  - Research Orchestrator                                     │
│  - Citation Engine                                          │
│  - Paper Ingestion Pipeline                                 │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
┌───────────────────┐ ┌───────────────┐ ┌───────────────┐
│   LightRAG        │ │   External    │ │   Supabase    │
│   (Hyperion)      │ │   APIs        │ │   Database    │
│   - PDF Upload    │ │   - Semantic  │ │   - Projects  │
│   - Auto-chunk    │ │     Scholar   │ │   - Sources   │
│   - Query + KG    │ │   - OpenAlex  │ │   - Citations │
└───────────────────┘ │   - arXiv     │ │   - Reports   │
                      └───────────────┘ └───────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Conda (for `bizon_mcp` environment)
- Access to Hyperion MCP (LightRAG)

### Installation

```bash
# Clone the repository
git clone https://github.com/SEERINTELAI/academic-research-tool.git
cd academic-research-tool

# Backend setup
conda activate bizon_mcp
pip install -r requirements.txt

# Frontend setup
cd frontend
npm install
```

### Environment Variables

```bash
# Backend
LIGHTRAG_API_KEY=your_lightrag_key
HYPERION_MCP_URL=https://n8n-dev-u36296.vm.elestio.app/mcp/hyperion
HYPERION_AUTH_TOKEN=your_auth_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
CLAUDE_API_KEY=your_claude_key

# External APIs (optional)
SEMANTIC_SCHOLAR_API_KEY=your_key
```

### Running

```bash
# Backend (runs on port 8003)
cd academic-research-tool
conda activate bizon_mcp
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8003

# Frontend (runs on port 3000)
cd frontend
npm run dev
```

### Verifying Setup

```bash
# Check backend health
curl http://localhost:8003/api/health

# Check system diagnostics
curl http://localhost:8003/api/health/diagnostics | python3 -m json.tool

# Run connectivity tests
pytest tests/e2e/test_connectivity.py -v
```

## Project Structure

```
academic-research-tool/
├── README.md                 # This file
├── ARCHITECTURE.md           # Detailed architecture
├── requirements.txt          # Python dependencies
├── planning/                 # Planning infrastructure
│   ├── MASTER_PLAN.md       # Feature index
│   ├── tasks.json           # Agent Farm task queue
│   ├── AK_RAG_VALIDATION.md # RAG validation results
│   └── features/            # Feature specifications
│       ├── AR1_outline_formation/
│       ├── AR2_research_ingestion/
│       ├── AR3_synthesis_rag/
│       ├── AR4_report_writing/
│       └── AR5_citation_management/
├── src/                      # Backend source code
│   ├── api/                 # FastAPI routes
│   ├── services/            # Business logic
│   └── models/              # Pydantic models
├── frontend/                 # Next.js frontend
├── tests/                    # Test suite
└── docs/                     # Documentation
```

## Development Status

| Category | Status | Features |
|----------|--------|----------|
| AR1: Outline Formation | ✅ Basic | Create/edit outline sections |
| AR2: Research & Ingestion | ✅ Done | Semantic Scholar search, PDF ingest via LightRAG |
| AR3: Synthesis (RAG) | ✅ Done | RAG query interface, knowledge tree discovery |
| AR4: Report Writing | ✅ MVP | Monaco editor, AI assist, citation insertion |
| AR5: Citation Management | 🔜 Partial | Basic citations, full formatting pending |

### Frontend Features

The UI has two main tabs per project:

#### Research Tab (4 sub-tabs + Chat)
- **Explore**: Candidate papers found via search (not yet ingested). Click "Ingest" to add to Library.
- **Library**: Ingested papers grouped by AI-detected topics (Zotero-like view)
- **Tree**: Visual knowledge graph of ingested papers and their relationships
- **Outline**: AI-generated outline with claims linked to supporting sources
- **Chat**: Always-visible AI assistant for searches, outline generation, etc.

#### Write Tab
- **Monaco Editor**: Professional writing interface
- **AI Writing Assist**: RAG-powered suggestions based on your research
- **Citation Insertion**: Click-to-cite from your sources
- **Auto-save**: Cmd+S or auto-save on changes

## Key Technologies

- **RAG**: LightRAG (graph-based RAG with automatic chunking)
  - Web UI: http://5.78.148.113:9621 (Documents, Knowledge Graph)
  - Handles PDF parsing, chunking, and indexing automatically
- **Academic APIs**: Semantic Scholar (paper search + citation graph)
- **LLM**: Claude API (via Cursor/AK)
- **Database**: Supabase (PostgreSQL)
- **Frontend**: Next.js, Monaco Editor
- **Backend**: FastAPI

## Related Documentation

- [Architecture Details](ARCHITECTURE.md)
- [Planning Overview](planning/README.md)
- [Feature Master Plan](planning/MASTER_PLAN.md)
- [AK RAG Validation](../../../planning/AK_RAG_DECISION_GATE.md)

## API Testing & Diagnostics

### Test Harness Endpoints

The API provides programmatic testing endpoints at `/api/test/*`:

| Endpoint | Description |
|----------|-------------|
| `POST /api/test/create-project` | Create a test project |
| `POST /api/test/search-papers` | Search for papers |
| `POST /api/test/ingest-paper` | Ingest a paper to RAG |
| `POST /api/test/generate-outline` | Generate an outline |
| `POST /api/test/full-research-flow` | Run complete E2E workflow |
| `GET /api/test/diagnostics` | Get system health info |
| `DELETE /api/test/cleanup/{id}` | Clean up test project |

### Diagnostics Endpoint

`GET /api/health/diagnostics` returns:
- Service health (database, LightRAG, Semantic Scholar)
- Recent errors (last 100)
- Request logs (last 100)
- Configuration info

### Frontend Test Harness

In development mode, access `window.__TEST_HARNESS__` in browser console:

```javascript
// Get all state
window.__TEST_HARNESS__.getState()

// Get React Query cache
window.__TEST_HARNESS__.getQueryCache()

// Get network request history
window.__TEST_HARNESS__.getNetworkHistory()

// Clear network history
window.__TEST_HARNESS__.clearNetworkHistory()
```

### Running Tests

```bash
# Connectivity tests (always pass even without DB)
pytest tests/e2e/test_connectivity.py -v

# Full lifecycle E2E tests (require Supabase)
pytest tests/e2e/test_full_lifecycle.py -v

# All E2E tests (require Supabase)
pytest tests/e2e/ -v

# All tests
pytest tests/ -v
```

### Full Lifecycle Test Coverage

The `test_full_lifecycle.py` test suite covers the complete research workflow:

| Test | Coverage |
|------|----------|
| `test_01_create_project` | Create a new research project |
| `test_02_search_papers` | Search for papers via chat |
| `test_03_ingest_papers` | Ingest papers to the library |
| `test_04_verify_library` | Verify sources in library with topic grouping |
| `test_05_verify_citation_tree` | Verify knowledge tree with citation edges |
| `test_06_generate_outline` | Generate outline via chat |
| `test_07_verify_outline_sources` | Verify outline sections have linked sources |
| `test_08_critique_outline` | AI critique and update outline sections |
| `test_09_generate_paper_draft` | Generate paper from outline |
| `test_10_verify_citations` | Verify paper has proper citations |

### Report Generation API

```bash
# Generate paper from outline
POST /api/projects/{id}/report/generate

# Get generated report
GET /api/projects/{id}/report

# Generate individual section
POST /api/projects/{id}/report/sections/{section_id}/write
```

## Contributing

This project uses the Agent Farm task system. See `planning/tasks.json` for current tasks.

## License

MIT

