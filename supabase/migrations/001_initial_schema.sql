-- Academic Research Tool - Initial Schema
-- Migration: 001_initial_schema
-- Date: 2025-12-28
-- Description: Core tables for research projects, sources, synthesis, and citations

-- ============================================================================
-- ENUMS
-- ============================================================================

CREATE TYPE project_status AS ENUM ('draft', 'active', 'completed', 'archived');

CREATE TYPE section_type AS ENUM (
    'introduction',
    'literature_review', 
    'methods',
    'results',
    'discussion',
    'conclusion',
    'abstract',
    'custom'
);

CREATE TYPE ingestion_status AS ENUM (
    'pending',
    'downloading',
    'parsing',
    'chunking',
    'ingesting',
    'ready',
    'failed'
);

CREATE TYPE block_type AS ENUM ('paragraph', 'heading', 'quote', 'list', 'figure');

CREATE TYPE chunk_section_type AS ENUM (
    'abstract',
    'introduction',
    'methods',
    'results',
    'discussion',
    'conclusion',
    'references',
    'acknowledgments',
    'appendix',
    'other'
);

-- ============================================================================
-- TABLES
-- ============================================================================

-- -----------------------------------------------------------------------------
-- project: Top-level container for a research paper
-- -----------------------------------------------------------------------------
CREATE TABLE project (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    status project_status NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE project IS 'Research project container - one per paper being written';

-- -----------------------------------------------------------------------------
-- outline_section: Hierarchical outline structure
-- -----------------------------------------------------------------------------
CREATE TABLE outline_section (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES outline_section(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    section_type section_type NOT NULL DEFAULT 'custom',
    questions JSONB DEFAULT '[]'::jsonb,  -- ["What does X say about Y?", ...]
    notes TEXT,
    order_index INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT valid_questions CHECK (jsonb_typeof(questions) = 'array')
);

COMMENT ON TABLE outline_section IS 'Hierarchical outline with research questions per section';
COMMENT ON COLUMN outline_section.questions IS 'Array of research questions this section should answer';
COMMENT ON COLUMN outline_section.order_index IS 'Position within parent for drag-drop reordering';

-- -----------------------------------------------------------------------------
-- source: Academic papers (metadata + ingestion state)
-- -----------------------------------------------------------------------------
CREATE TABLE source (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    
    -- Paper identification
    doi TEXT,
    title TEXT NOT NULL,
    authors JSONB DEFAULT '[]'::jsonb,  -- [{name, affiliation, orcid}, ...]
    
    -- Publication info
    abstract TEXT,
    publication_year INTEGER,
    journal TEXT,
    volume TEXT,
    issue TEXT,
    pages TEXT,
    
    -- Source URLs
    pdf_url TEXT,
    semantic_scholar_id TEXT,
    arxiv_id TEXT,
    
    -- Ingestion state
    ingestion_status ingestion_status NOT NULL DEFAULT 'pending',
    hyperion_doc_name TEXT,  -- matches documentName in Hyperion/LightRAG
    chunk_count INTEGER DEFAULT 0,
    error_message TEXT,
    
    -- Metadata
    keywords JSONB DEFAULT '[]'::jsonb,
    citation_count INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT valid_authors CHECK (jsonb_typeof(authors) = 'array'),
    CONSTRAINT valid_keywords CHECK (jsonb_typeof(keywords) = 'array'),
    CONSTRAINT unique_doi_per_project UNIQUE (project_id, doi)
);

COMMENT ON TABLE source IS 'Academic papers - tracked from discovery through ingestion';
COMMENT ON COLUMN source.hyperion_doc_name IS 'Document identifier in Hyperion/LightRAG for chunk retrieval';
COMMENT ON COLUMN source.ingestion_status IS 'Pipeline state: pending → downloading → parsing → chunking → ingesting → ready';

-- -----------------------------------------------------------------------------
-- chunk: Pointers to text chunks stored in Hyperion
-- -----------------------------------------------------------------------------
CREATE TABLE chunk (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES source(id) ON DELETE CASCADE,
    
    -- Hyperion reference
    hyperion_chunk_id TEXT NOT NULL,
    
    -- Chunk metadata
    section_type chunk_section_type NOT NULL DEFAULT 'other',
    page_number INTEGER,
    text_preview TEXT,  -- First 300 chars for UI display
    chunk_index INTEGER NOT NULL DEFAULT 0,  -- Order within source
    
    -- For citation purposes
    paragraph_number INTEGER,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE chunk IS 'Pointers to Hyperion chunks with local metadata for citation';
COMMENT ON COLUMN chunk.hyperion_chunk_id IS 'LightRAG internal chunk ID from ingest response';
COMMENT ON COLUMN chunk.text_preview IS 'First 300 chars for UI display without Hyperion roundtrip';

-- -----------------------------------------------------------------------------
-- synthesis: Q&A results from RAG queries
-- -----------------------------------------------------------------------------
CREATE TABLE synthesis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    outline_section_id UUID REFERENCES outline_section(id) ON DELETE SET NULL,
    
    -- Query and response
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    
    -- Source attribution
    chunk_ids UUID[] DEFAULT '{}',  -- References to chunk.id
    
    -- Model info
    model TEXT DEFAULT 'claude-3-5-sonnet',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE synthesis IS 'RAG query results with source attribution for audit trail';
COMMENT ON COLUMN synthesis.chunk_ids IS 'Array of chunk IDs that contributed to this response';

-- -----------------------------------------------------------------------------
-- report_block: Document content blocks with versioning
-- -----------------------------------------------------------------------------
CREATE TABLE report_block (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    outline_section_id UUID REFERENCES outline_section(id) ON DELETE SET NULL,
    
    -- Content
    content TEXT NOT NULL DEFAULT '',
    block_type block_type NOT NULL DEFAULT 'paragraph',
    
    -- Ordering
    order_index INTEGER NOT NULL DEFAULT 0,
    
    -- Versioning
    version INTEGER NOT NULL DEFAULT 1,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE report_block IS 'Document content blocks - paragraph, heading, quote, etc.';
COMMENT ON COLUMN report_block.version IS 'Increments on each content edit for history tracking';

-- -----------------------------------------------------------------------------
-- report_block_history: Version history for report blocks
-- -----------------------------------------------------------------------------
CREATE TABLE report_block_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    block_id UUID NOT NULL REFERENCES report_block(id) ON DELETE CASCADE,
    
    -- Snapshot
    content TEXT NOT NULL,
    version INTEGER NOT NULL,
    
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE report_block_history IS 'Automatic snapshots of previous block versions';

-- -----------------------------------------------------------------------------
-- citation: In-text citations linking report to sources (APA format)
-- -----------------------------------------------------------------------------
CREATE TABLE citation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_block_id UUID NOT NULL REFERENCES report_block(id) ON DELETE CASCADE,
    
    -- Source links
    source_id UUID NOT NULL REFERENCES source(id) ON DELETE CASCADE,
    chunk_id UUID REFERENCES chunk(id) ON DELETE SET NULL,
    synthesis_id UUID REFERENCES synthesis(id) ON DELETE SET NULL,
    
    -- APA citation format
    in_text_citation TEXT NOT NULL,  -- "(Smith & Jones, 2020)" or "(Smith et al., 2020)"
    page_or_para TEXT,  -- "p. 42" or "para. 3"
    
    -- Quote handling
    is_direct_quote BOOLEAN NOT NULL DEFAULT false,
    quote_text TEXT,
    
    -- Position in block content
    char_offset_start INTEGER,
    char_offset_end INTEGER,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE citation IS 'In-text citations with full provenance chain to source';
COMMENT ON COLUMN citation.in_text_citation IS 'APA format: (Author, Year) or (Author1 & Author2, Year) or (Author et al., Year)';

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Project lookups
CREATE INDEX idx_project_status ON project(status);

-- Outline navigation
CREATE INDEX idx_outline_project ON outline_section(project_id);
CREATE INDEX idx_outline_parent ON outline_section(parent_id);
CREATE INDEX idx_outline_order ON outline_section(project_id, parent_id, order_index);

-- Source lookups
CREATE INDEX idx_source_project ON source(project_id);
CREATE INDEX idx_source_status ON source(ingestion_status);
CREATE INDEX idx_source_doi ON source(doi) WHERE doi IS NOT NULL;
CREATE INDEX idx_source_hyperion ON source(hyperion_doc_name) WHERE hyperion_doc_name IS NOT NULL;

-- Chunk lookups
CREATE INDEX idx_chunk_source ON chunk(source_id);
CREATE INDEX idx_chunk_hyperion ON chunk(hyperion_chunk_id);
CREATE INDEX idx_chunk_section ON chunk(source_id, section_type);

-- Synthesis lookups
CREATE INDEX idx_synthesis_project ON synthesis(project_id);
CREATE INDEX idx_synthesis_section ON synthesis(outline_section_id) WHERE outline_section_id IS NOT NULL;

-- Report block lookups
CREATE INDEX idx_block_project ON report_block(project_id);
CREATE INDEX idx_block_section ON report_block(outline_section_id) WHERE outline_section_id IS NOT NULL;
CREATE INDEX idx_block_order ON report_block(project_id, order_index);

-- Block history lookups
CREATE INDEX idx_history_block ON report_block_history(block_id);
CREATE INDEX idx_history_version ON report_block_history(block_id, version);

-- Citation lookups
CREATE INDEX idx_citation_block ON citation(report_block_id);
CREATE INDEX idx_citation_source ON citation(source_id);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER project_updated_at
    BEFORE UPDATE ON project
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER outline_updated_at
    BEFORE UPDATE ON outline_section
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER source_updated_at
    BEFORE UPDATE ON source
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER block_updated_at
    BEFORE UPDATE ON report_block
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Version history for report blocks
CREATE OR REPLACE FUNCTION save_block_history()
RETURNS TRIGGER AS $$
BEGIN
    -- Only save history if content actually changed
    IF OLD.content IS DISTINCT FROM NEW.content THEN
        INSERT INTO report_block_history (block_id, content, version, changed_at)
        VALUES (OLD.id, OLD.content, OLD.version, now());
        
        NEW.version := OLD.version + 1;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER block_history_trigger
    BEFORE UPDATE ON report_block
    FOR EACH ROW
    EXECUTE FUNCTION save_block_history();

-- Update chunk count on source when chunks are added/removed
CREATE OR REPLACE FUNCTION update_chunk_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE source SET chunk_count = chunk_count + 1 WHERE id = NEW.source_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE source SET chunk_count = chunk_count - 1 WHERE id = OLD.source_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER chunk_count_trigger
    AFTER INSERT OR DELETE ON chunk
    FOR EACH ROW
    EXECUTE FUNCTION update_chunk_count();

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Generate APA in-text citation from source
CREATE OR REPLACE FUNCTION generate_apa_citation(source_row source)
RETURNS TEXT AS $$
DECLARE
    author_count INTEGER;
    first_author TEXT;
    second_author TEXT;
    citation TEXT;
BEGIN
    -- Count authors
    author_count := jsonb_array_length(source_row.authors);
    
    IF author_count = 0 THEN
        -- No author - use title
        citation := '(' || LEFT(source_row.title, 30) || ', ' || COALESCE(source_row.publication_year::TEXT, 'n.d.') || ')';
    ELSIF author_count = 1 THEN
        -- Single author: (Smith, 2020)
        first_author := source_row.authors->0->>'name';
        -- Extract last name (assume "First Last" format)
        first_author := split_part(first_author, ' ', array_length(string_to_array(first_author, ' '), 1));
        citation := '(' || first_author || ', ' || COALESCE(source_row.publication_year::TEXT, 'n.d.') || ')';
    ELSIF author_count = 2 THEN
        -- Two authors: (Smith & Jones, 2020)
        first_author := source_row.authors->0->>'name';
        first_author := split_part(first_author, ' ', array_length(string_to_array(first_author, ' '), 1));
        second_author := source_row.authors->1->>'name';
        second_author := split_part(second_author, ' ', array_length(string_to_array(second_author, ' '), 1));
        citation := '(' || first_author || ' & ' || second_author || ', ' || COALESCE(source_row.publication_year::TEXT, 'n.d.') || ')';
    ELSE
        -- Three or more: (Smith et al., 2020)
        first_author := source_row.authors->0->>'name';
        first_author := split_part(first_author, ' ', array_length(string_to_array(first_author, ' '), 1));
        citation := '(' || first_author || ' et al., ' || COALESCE(source_row.publication_year::TEXT, 'n.d.') || ')';
    END IF;
    
    RETURN citation;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION generate_apa_citation IS 'Generate APA 7th edition in-text citation from source record';

-- ============================================================================
-- SEED DATA (Optional - for testing)
-- ============================================================================

-- Uncomment to create a sample project for testing
/*
INSERT INTO project (title, description, status) VALUES
('Climate Change Effects on Agriculture', 'Research on how climate change affects crop yields globally', 'active');
*/

