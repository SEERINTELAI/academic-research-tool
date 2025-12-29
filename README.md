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
│  - Monaco Editor (writing interface)                        │
│  - Outline Panel                                            │
│  - Source Library                                           │
│  - Research Chat                                            │
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
# Backend
cd src
uvicorn main:app --reload

# Frontend
cd frontend
npm run dev
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

### Frontend Features (AR4)

- **Project Management**: Create, list, archive projects
- **Outline Editor**: Hierarchical section management with types
- **Sources Library**: Search papers, add to project, ingest to LightRAG
- **Discovery Panel**: Explore references, citations, and related papers
- **Monaco Editor**: Professional writing interface with:
  - AI Writing Assist (RAG-powered)
  - Click-to-cite from sources panel
  - Auto-save (Cmd+S)
- **Research Chat**: Ask questions about ingested papers

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

## Contributing

This project uses the Agent Farm task system. See `planning/tasks.json` for current tasks.

## License

MIT

