# Academic Research Tool - Planning

This directory contains the planning infrastructure for the Academic Research Tool project.

## Structure

```
planning/
├── README.md          # This file
├── MASTER_PLAN.md     # Feature index and status
├── tasks.json         # Agent Farm task queue
├── AK_RAG_VALIDATION.md  # RAG validation results
└── features/          # Feature specifications
    ├── AR1_outline_formation/
    ├── AR2_research_ingestion/
    ├── AR3_synthesis_rag/
    ├── AR4_report_writing/
    └── AR5_citation_management/
```

## Feature Categories

| ID | Category | Description | Features |
|----|----------|-------------|----------|
| AR1 | Outline Formation | Collaborative research outline structuring | 4 |
| AR2 | Research & Ingestion | Academic paper search, retrieval, PDF parsing | 6 |
| AR3 | Synthesis (RAG) | Query papers via Hyperion, cited answers | 5 |
| AR4 | Report Writing | Collaborative editor with AI assistance | 5 |
| AR5 | Citation Management | Citation provenance, formatting, export | 4 |

## Workflow

1. Features are planned in `MASTER_PLAN.md`
2. Detailed specs go in `features/{category}/`
3. Tasks are queued in `tasks.json` for Agent Farm
4. Agents pick up tasks and implement

## Task States

- `pending` - Not started
- `in_progress` - Being worked on
- `completed` - Done
- `cancelled` - Abandoned

## Dependencies

Tasks declare dependencies on other tasks. Blocked tasks won't be picked up until dependencies complete.

## Related

- [RAG Validation](../../planning/AK_RAG_DECISION_GATE.md) - Hyperion/LightRAG validation results
- [Architecture](../ARCHITECTURE.md) - System architecture

