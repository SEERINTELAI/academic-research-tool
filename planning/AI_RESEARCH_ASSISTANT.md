# AI Research Assistant - Architecture

## Overview

The Research tab has **4 sub-tabs** that represent different stages of the research workflow:

1. **Explore** - Discover candidate papers (not yet ingested)
2. **Library** - Browse ingested papers grouped by AI-detected topic
3. **Tree** - Visual knowledge graph of papers and relationships
4. **Outline** - Auto-generated outline with claims linked to sources

Plus an **always-visible Chat panel** for AI interaction.

## Core Concept

```
┌─────────────────────────────────────────────────────────────┐
│                     Research Tab (4 Sub-tabs)               │
├────────────┬────────────┬────────────┬────────────┬─────────┤
│  Explore   │  Library   │    Tree    │  Outline   │  Chat   │
│ (search)   │ (ingested) │  (graph)   │ (claims)   │ (AI)    │
├────────────┴────────────┴────────────┴────────────┼─────────┤
│                                                    │ Always  │
│  [Selected tab content]                            │ visible │
│                                                    │         │
│  Details panel (when item selected)                │         │
└────────────────────────────────────────────────────┴─────────┘

Flow:
  Search → Explore → Ingest → Library → Tree → Outline
           (candidates)  (grouped)  (graph) (claims)
```

## Tab Purposes

| Tab | Data Source | Purpose |
|-----|-------------|---------|
| **Explore** | `knowledge_node` (is_ingested=false) | Candidate papers from search - review and ingest |
| **Library** | `source` table | Ingested papers grouped by AI-detected topic |
| **Tree** | `knowledge_node` (is_ingested=true) | Visual graph of papers and relationships |
| **Outline** | `outline_claim` + sources | Claims with supporting source links |

## Data Model

### Research Session
```
research_session:
  id: uuid
  project_id: uuid
  topic: string                    # "post-quantum cryptography"
  status: exploring | drafting | refining
  created_at, updated_at
```

### Knowledge Node (in knowledge tree)
```
knowledge_node:
  id: uuid
  session_id: uuid
  source_id: uuid (nullable)       # null for AI-generated summaries
  parent_node_id: uuid (nullable)  # tree structure
  
  node_type: source | claim | topic | summary
  content: string                  # the text/summary
  confidence: float                # AI confidence in relevance
  
  user_rating: useful | neutral | irrelevant (nullable)
  user_note: string (nullable)     # user critique
  
  created_at
```

### Outline Claim (links outline to sources)
```
outline_claim:
  id: uuid
  section_id: uuid                 # outline_section.id
  claim_text: string               # "Lattice-based schemes are quantum-resistant"
  order_index: int
  
  supporting_nodes: uuid[]         # knowledge_node IDs that back this claim
  evidence_strength: strong | moderate | weak | needs_more
  
  user_critique: string (nullable) # "need more papers for this"
  status: draft | reviewed | approved
```

## API Endpoints

### Research Session
```
POST   /api/projects/{id}/research/session          # Start research session
GET    /api/projects/{id}/research/session          # Get current session
POST   /api/projects/{id}/research/session/explore  # AI explores topic
POST   /api/projects/{id}/research/session/deepen   # Go deeper on subtopic
```

### Knowledge Tree
```
GET    /api/projects/{id}/research/knowledge        # Get knowledge tree
PATCH  /api/projects/{id}/research/knowledge/{node_id}  # Rate/critique node
DELETE /api/projects/{id}/research/knowledge/{node_id}  # Remove node
POST   /api/projects/{id}/research/knowledge/suggest    # Suggest new direction
```

### Auto-Outline
```
POST   /api/projects/{id}/outline/generate          # Generate from knowledge
GET    /api/projects/{id}/outline/claims            # Get claims with sources
PATCH  /api/projects/{id}/outline/claims/{id}       # Critique claim
POST   /api/projects/{id}/outline/claims/{id}/expand  # Request expansion
```

## UI Components

### Research Tab
```
┌──────────────────────────────────────────────────────────┐
│ 🔬 Research: Post-Quantum Cryptography                   │
├──────────────────────────────────────────────────────────┤
│ [Chat Input: "Focus more on lattice-based schemes..."]   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ ▼ Lattice-Based Cryptography (5 sources)                │
│   ├─ 📄 "NTRU: A Ring-Based Public Key..." (Hoffstein)  │
│   │     Summary: Introduces NTRU, a lattice-based...    │
│   │     [👍 Useful] [👎 Irrelevant] [💬 Note]           │
│   │                                                      │
│   ├─ 📄 "Learning With Errors..." (Regev)               │
│   │     Summary: Foundational LWE problem...            │
│   │     [👍 Useful] [👎 Irrelevant] [💬 Note]           │
│   │                                                      │
│   └─ + 3 more sources                                    │
│                                                          │
│ ▼ Hash-Based Signatures (3 sources)                     │
│   └─ ...                                                 │
│                                                          │
│ [+ Suggest: "Find more on..."]                          │
└──────────────────────────────────────────────────────────┘
```

### Outline Tab (with source links)
```
┌──────────────────────────────────────────────────────────┐
│ 📝 Outline                              [Generate Draft] │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ ▼ 1. Introduction                                        │
│   │                                                      │
│   ├─ "Quantum computers threaten current cryptography"   │
│   │   Sources: [Shor94] [Preskill18]  ✓ Strong evidence │
│   │                                                      │
│   └─ "Post-quantum schemes are being standardized"       │
│       Sources: [NIST22]  ⚠️ Needs more papers           │
│       [+ Request more sources] [✗ Remove claim]         │
│                                                          │
│ ▼ 2. Lattice-Based Approaches                           │
│   │                                                      │
│   ├─ "LWE provides provable security guarantees"         │
│   │   Sources: [Regev05] [Peikert16]  ✓ Strong          │
│   │                                                      │
│   └─ "NTRU offers efficient key sizes"                   │
│       Sources: [Hoffstein98]  ⚠️ Single source          │
│       [+ Request more sources] [✗ Remove claim]         │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## AI Agent Workflow

### 1. Exploration Phase
```python
async def explore_topic(session_id, topic, user_guidance=None):
    # 1. Search for papers
    papers = await semantic_scholar.search(topic, limit=20)
    
    # 2. Filter by relevance (AI judges)
    relevant = await ai.filter_relevant(papers, topic, user_guidance)
    
    # 3. Auto-ingest top papers
    for paper in relevant[:10]:
        await hyperion.ingest(paper)
        await create_knowledge_node(paper, session_id)
    
    # 4. Generate summaries
    summaries = await ai.summarize_findings(relevant)
    
    # 5. Identify subtopics for deeper exploration
    subtopics = await ai.identify_subtopics(summaries)
    
    return {
        "ingested": len(relevant),
        "summaries": summaries,
        "suggested_subtopics": subtopics
    }
```

### 2. Knowledge Condensation
```python
async def generate_outline_from_knowledge(session_id):
    # 1. Get all knowledge nodes
    nodes = await get_knowledge_tree(session_id)
    
    # 2. Cluster into themes
    themes = await ai.cluster_themes(nodes)
    
    # 3. Generate outline structure
    outline = await ai.generate_outline(themes)
    
    # 4. For each section, identify supporting claims
    for section in outline.sections:
        claims = await ai.extract_claims(section, nodes)
        for claim in claims:
            # Link claim to source nodes
            supporting = await ai.find_supporting_nodes(claim, nodes)
            await create_outline_claim(section, claim, supporting)
    
    return outline
```

### 3. User Feedback Loop
```python
async def handle_user_critique(claim_id, critique_type, details):
    claim = await get_claim(claim_id)
    
    if critique_type == "needs_more_sources":
        # Search for more papers on this specific claim
        papers = await search_for_claim_support(claim.claim_text)
        await auto_ingest(papers)
        await update_claim_sources(claim_id, papers)
        
    elif critique_type == "irrelevant":
        # Remove claim and potentially related sources
        await mark_claim_irrelevant(claim_id)
        await suggest_knowledge_pruning(claim.supporting_nodes)
        
    elif critique_type == "expand":
        # Generate sub-claims or deeper exploration
        expansion = await ai.expand_claim(claim)
        await create_child_claims(claim_id, expansion)
```

## Implementation Order

1. **Database schema** - Add research_session, knowledge_node, outline_claim tables
2. **Research session API** - Start session, explore topic
3. **Knowledge tree API** - CRUD for knowledge nodes
4. **Auto-ingest pipeline** - Search → filter → ingest automatically
5. **Outline generation** - AI generates outline from knowledge
6. **Claim linking** - Connect outline claims to source nodes
7. **Critique API** - Handle user feedback
8. **Research tab UI** - Knowledge tree view with ratings
9. **Outline tab updates** - Show claims with source links

## Migration SQL

```sql
-- Research sessions
CREATE TABLE research_session (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'exploring',
    guidance_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Knowledge tree nodes
CREATE TABLE knowledge_node (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES research_session(id) ON DELETE CASCADE,
    source_id UUID REFERENCES source(id) ON DELETE SET NULL,
    parent_node_id UUID REFERENCES knowledge_node(id) ON DELETE CASCADE,
    
    node_type TEXT NOT NULL, -- 'source', 'claim', 'topic', 'summary'
    content TEXT NOT NULL,
    summary TEXT,
    confidence FLOAT DEFAULT 0.5,
    
    user_rating TEXT, -- 'useful', 'neutral', 'irrelevant'
    user_note TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Outline claims with source links
CREATE TABLE outline_claim (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id UUID NOT NULL REFERENCES outline_section(id) ON DELETE CASCADE,
    claim_text TEXT NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 0,
    
    supporting_nodes UUID[] DEFAULT '{}',
    evidence_strength TEXT DEFAULT 'moderate',
    
    user_critique TEXT,
    status TEXT DEFAULT 'draft',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_knowledge_node_session ON knowledge_node(session_id);
CREATE INDEX idx_knowledge_node_parent ON knowledge_node(parent_node_id);
CREATE INDEX idx_outline_claim_section ON outline_claim(section_id);
```

