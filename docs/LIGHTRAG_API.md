# LightRAG API Reference

LightRAG is the RAG backend powering Hyperion. It provides:
- Document ingestion with automatic chunking
- Knowledge graph construction
- Multiple query modes
- Full entity/relationship CRUD

## Endpoint

```
http://5.78.148.113:9621
```

**Authentication**: API Key via header (managed by Hyperion MCP)

**Swagger Docs**: http://5.78.148.113:9621/docs

---

## Query Modes

LightRAG supports multiple query strategies:

| Mode | Description | Returns |
|------|-------------|---------|
| `local` | Entities + direct relationships + chunks | Focused, entity-centric |
| `global` | Relationship patterns across graph | Broad patterns |
| `hybrid` | Combines local and global | Balanced |
| `naive` | Vector search only (no graph) | Just text chunks |
| `mix` | Knowledge graph + vector chunks | **Default, recommended** |
| `bypass` | Skip retrieval, direct to LLM | No RAG context |

### Query Request

```json
POST /query
{
  "query": "machine learning algorithms",
  "mode": "mix",
  "only_need_context": false,
  "top_k": 10
}
```

### Query Response

```json
{
  "response": "Generated response text...",
  "references": [
    {
      "reference_id": "abc123",
      "file_path": "paper.pdf",
      "content": ["chunk1 text", "chunk2 text"]
    }
  ]
}
```

---

## Data Query (No LLM)

Use `/query/data` to get raw retrieval without LLM generation:

```json
POST /query/data
{
  "query": "What is RAG?",
  "mode": "local"
}
```

Returns:
- `entities`: Knowledge graph entities
- `relationships`: Entity connections
- `chunks`: Text segments
- `references`: Source file mappings
- `metadata`: Processing info, keywords

---

## Document Ingestion

### Single Text

```json
POST /documents/text
{
  "text": "Content to insert...",
  "file_source": "paper_name.pdf"
}
```

### Multiple Texts

```json
POST /documents/texts
{
  "texts": ["text1", "text2"],
  "file_sources": ["source1", "source2"]
}
```

### File Upload

```
POST /documents/upload
Content-Type: multipart/form-data
file: <PDF or text file>
```

**LightRAG handles chunking automatically** when you insert text or upload files.

---

## Knowledge Graph API

### List Entities

```
GET /graph/label/list
```

### Search Entities

```
GET /graph/label/search?query=term
```

### Create Entity

```json
POST /graph/entity/create
{
  "entity_name": "Machine Learning",
  "entity_data": {
    "description": "A branch of AI...",
    "entity_type": "CONCEPT"
  }
}
```

### Create Relationship

```json
POST /graph/relation/create
{
  "source_entity": "Deep Learning",
  "target_entity": "Machine Learning",
  "relation_data": {
    "description": "Deep learning is a subset of machine learning",
    "keywords": "subset, technique",
    "weight": 1.0
  }
}
```

### Edit Entity

```json
POST /graph/entity/edit
{
  "entity_name": "Machine Learning",
  "updated_data": {"description": "Updated description"},
  "allow_rename": false,
  "allow_merge": false
}
```

### Merge Entities

```json
POST /graph/entities/merge
{
  // Merge duplicate entities
}
```

---

## Document Management

### List Documents

```
GET /documents
```

Returns documents grouped by status: PENDING, PROCESSING, PROCESSED, FAILED

### Delete Document

```json
DELETE /documents/delete_document
{
  "doc_ids": ["doc1", "doc2"]
}
```

### Pipeline Status

```
GET /documents/pipeline_status
```

Returns current processing status, batch info, progress.

---

## Implications for Academic Research Tool

### Chunking Strategy

**LightRAG handles chunking internally**. Our options:

1. **Simple Path**: Upload PDFs directly via `/documents/upload`
   - LightRAG chunks automatically
   - Less control over chunk boundaries
   - Faster to implement

2. **Current Path**: GROBID + custom chunking → `/documents/texts`
   - Section-aware chunks
   - Embedded metadata in text
   - Better provenance tracking

**Recommendation**: Keep current approach for academic papers (section awareness is valuable), but consider simple upload for auxiliary documents.

### Knowledge Graph Opportunities

LightRAG builds a knowledge graph from ingested content. We could:

1. **Query the graph** via `/query/data` to get entities/relationships
2. **Create custom entities** for key concepts in research
3. **Create relationships** between papers (extends beyond citation links)
4. **Explore the graph** to find conceptual connections

### Future Enhancements

- [ ] Use `/query/data` to surface entity relationships in UI
- [ ] Allow manual entity creation for research concepts
- [ ] Visualize the knowledge graph for a project
- [ ] Use graph traversal for multi-hop reasoning

