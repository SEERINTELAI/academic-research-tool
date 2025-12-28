# Database Schema

**Last Updated**: 2025-12-28  
**Migration**: `001_initial_schema.sql`

## Overview

The database tracks research projects from outline through final document with full citation provenance.

```
project
  ├── outline_section (hierarchical)
  ├── source (papers)
  │     └── chunk (Hyperion pointers)
  ├── synthesis (Q&A history)
  ├── report_block (document content)
  │     └── report_block_history (versions)
  └── citation (links blocks ↔ sources)
```

---

## Tables

### `project`

Top-level container for a research paper.

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| title | text | Project title |
| description | text | Research question/scope |
| status | enum | draft, active, completed, archived |
| created_at | timestamptz | |
| updated_at | timestamptz | Auto-updated |

---

### `outline_section`

Hierarchical outline with research questions.

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| project_id | uuid | FK → project |
| parent_id | uuid | FK → self (for nesting) |
| title | text | Section title |
| section_type | enum | introduction, methods, results, etc. |
| questions | jsonb | ["Question 1", "Question 2"] |
| notes | text | Scope notes |
| order_index | int | Position for drag-drop |
| created_at | timestamptz | |
| updated_at | timestamptz | |

**Reordering**: Update `order_index` and optionally `parent_id` on drag-drop.

---

### `source`

Academic papers with ingestion tracking.

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| project_id | uuid | FK → project |
| doi | text | Paper DOI (unique per project) |
| title | text | Paper title |
| authors | jsonb | [{name, affiliation, orcid}, ...] |
| abstract | text | Paper abstract |
| publication_year | int | For APA citation |
| journal | text | Publication venue |
| pdf_url | text | Source PDF URL |
| ingestion_status | enum | pending → downloading → parsing → chunking → ingesting → ready |
| hyperion_doc_name | text | Document name in LightRAG |
| chunk_count | int | Auto-incremented by trigger |
| error_message | text | If ingestion failed |
| created_at | timestamptz | |
| updated_at | timestamptz | |

**Pipeline States**:
```
pending → downloading → parsing → chunking → ingesting → ready
                                                      ↘ failed
```

---

### `chunk`

Pointers to Hyperion/LightRAG chunks.

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| source_id | uuid | FK → source |
| hyperion_chunk_id | text | LightRAG chunk ID |
| section_type | enum | abstract, methods, results, etc. |
| page_number | int | Page in original PDF |
| text_preview | text | First 300 chars for UI |
| chunk_index | int | Order within source |
| created_at | timestamptz | |

**Note**: Full text lives in Hyperion. We only store metadata + preview.

---

### `synthesis`

RAG query results with source attribution.

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| project_id | uuid | FK → project |
| outline_section_id | uuid | FK → outline_section (nullable) |
| query | text | User's question |
| response | text | AI-generated answer |
| chunk_ids | uuid[] | Chunks that contributed |
| model | text | LLM used (e.g., claude-3-5-sonnet) |
| created_at | timestamptz | |

---

### `report_block`

Document content with versioning.

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| project_id | uuid | FK → project |
| outline_section_id | uuid | FK → outline_section (nullable) |
| content | text | Block content |
| block_type | enum | paragraph, heading, quote, list, figure |
| order_index | int | Position in document |
| version | int | Increments on edit |
| created_at | timestamptz | |
| updated_at | timestamptz | |

**Version History**: Trigger saves old content to `report_block_history` before UPDATE.

---

### `report_block_history`

Automatic version snapshots.

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| block_id | uuid | FK → report_block |
| content | text | Previous content |
| version | int | Which version |
| changed_at | timestamptz | When changed |

---

### `citation`

In-text citations with full provenance (APA format).

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| report_block_id | uuid | FK → report_block |
| source_id | uuid | FK → source |
| chunk_id | uuid | FK → chunk (nullable) |
| synthesis_id | uuid | FK → synthesis (nullable) |
| in_text_citation | text | "(Smith et al., 2020)" |
| page_or_para | text | "p. 42" |
| is_direct_quote | bool | Direct quote flag |
| quote_text | text | The quoted text |
| char_offset_start | int | Position in block |
| char_offset_end | int | |
| created_at | timestamptz | |

---

## Enums

```sql
project_status: draft, active, completed, archived

section_type: introduction, literature_review, methods, results, 
              discussion, conclusion, abstract, custom

ingestion_status: pending, downloading, parsing, chunking, 
                  ingesting, ready, failed

block_type: paragraph, heading, quote, list, figure

chunk_section_type: abstract, introduction, methods, results,
                    discussion, conclusion, references, 
                    acknowledgments, appendix, other
```

---

## Key Relationships

```
Citation Provenance Chain:
report_block.citation → chunk → source → PDF page

Synthesis Attribution:
synthesis.chunk_ids[] → chunk[] → source[]

Outline Structure:
outline_section.parent_id → outline_section (tree)
```

---

## Triggers

| Trigger | Table | Purpose |
|---------|-------|---------|
| `project_updated_at` | project | Auto-update timestamp |
| `outline_updated_at` | outline_section | Auto-update timestamp |
| `source_updated_at` | source | Auto-update timestamp |
| `block_updated_at` | report_block | Auto-update timestamp |
| `block_history_trigger` | report_block | Save version history |
| `chunk_count_trigger` | chunk | Update source.chunk_count |

---

## Helper Functions

### `generate_apa_citation(source)`

Generates APA 7th edition in-text citation:

| Authors | Output |
|---------|--------|
| 1 | (Smith, 2020) |
| 2 | (Smith & Jones, 2020) |
| 3+ | (Smith et al., 2020) |
| 0 | (Title..., 2020) |

---

## Data Flow

```
1. User creates project
   INSERT INTO project

2. User builds outline
   INSERT INTO outline_section (with parent_id for nesting)

3. User searches for papers
   API call to Semantic Scholar
   INSERT INTO source (status: pending)

4. Background job ingests paper
   UPDATE source (status: downloading)
   Fetch PDF
   UPDATE source (status: parsing)
   GROBID extracts sections
   UPDATE source (status: chunking)
   Split into chunks
   UPDATE source (status: ingesting)
   Call Hyperion ingest_multiple_knowledge
   INSERT INTO chunk (for each chunk)
   UPDATE source (status: ready, hyperion_doc_name: ...)

5. User asks question
   Query Hyperion → get chunk_ids
   Generate response with Claude
   INSERT INTO synthesis (query, response, chunk_ids)

6. User writes report
   INSERT INTO report_block
   (Edits trigger history saves)

7. User inserts citation
   INSERT INTO citation (linking block ↔ source ↔ chunk)
```

---

## Migration Location

```
supabase/migrations/001_initial_schema.sql
```

To apply:
```bash
supabase db push
# or
psql -f supabase/migrations/001_initial_schema.sql
```

