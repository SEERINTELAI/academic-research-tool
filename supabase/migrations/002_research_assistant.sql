-- Migration: Add AI Research Assistant tables
-- Created: 2024-12-29
-- Description: Research sessions, knowledge tree, and outline claims with source linking

-- ============================================================================
-- Research Sessions
-- ============================================================================
-- Tracks an ongoing research exploration for a project

CREATE TABLE IF NOT EXISTS research_session (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    
    topic TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'exploring'
        CHECK (status IN ('exploring', 'drafting', 'refining', 'completed')),
    
    -- User guidance for AI direction
    guidance_notes TEXT,
    
    -- Stats
    sources_ingested INTEGER DEFAULT 0,
    nodes_created INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_research_session_project ON research_session(project_id);

-- ============================================================================
-- Knowledge Tree Nodes
-- ============================================================================
-- Hierarchical knowledge structure built during research

CREATE TABLE IF NOT EXISTS knowledge_node (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES research_session(id) ON DELETE CASCADE,
    
    -- Optional link to ingested source
    source_id UUID REFERENCES source(id) ON DELETE SET NULL,
    
    -- Tree structure (null parent = root node)
    parent_node_id UUID REFERENCES knowledge_node(id) ON DELETE CASCADE,
    
    -- Node content
    node_type TEXT NOT NULL 
        CHECK (node_type IN ('topic', 'source', 'claim', 'summary', 'question')),
    title TEXT NOT NULL,
    content TEXT,  -- Full content/summary
    
    -- AI metadata
    confidence FLOAT DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),
    relevance_score FLOAT DEFAULT 0.5,
    
    -- User feedback
    user_rating TEXT CHECK (user_rating IN ('useful', 'neutral', 'irrelevant')),
    user_note TEXT,
    is_hidden BOOLEAN DEFAULT FALSE,  -- User marked as irrelevant but kept for history
    
    -- Ordering within siblings
    order_index INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_knowledge_node_session ON knowledge_node(session_id);
CREATE INDEX idx_knowledge_node_parent ON knowledge_node(parent_node_id);
CREATE INDEX idx_knowledge_node_source ON knowledge_node(source_id);
CREATE INDEX idx_knowledge_node_type ON knowledge_node(node_type);

-- ============================================================================
-- Outline Claims
-- ============================================================================
-- Links outline sections to supporting evidence from knowledge tree

CREATE TABLE IF NOT EXISTS outline_claim (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id UUID NOT NULL REFERENCES outline_section(id) ON DELETE CASCADE,
    
    -- The claim itself
    claim_text TEXT NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 0,
    
    -- Supporting evidence (array of knowledge_node IDs)
    supporting_nodes UUID[] DEFAULT '{}',
    
    -- Evidence assessment
    evidence_strength TEXT DEFAULT 'moderate'
        CHECK (evidence_strength IN ('strong', 'moderate', 'weak', 'needs_more', 'none')),
    source_count INTEGER DEFAULT 0,
    
    -- User feedback
    user_critique TEXT,
    status TEXT DEFAULT 'draft'
        CHECK (status IN ('draft', 'reviewed', 'approved', 'rejected')),
    
    -- AI can suggest actions
    suggested_action TEXT,  -- e.g., "find_more_sources", "expand", "merge_with_X"
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_outline_claim_section ON outline_claim(section_id);
CREATE INDEX idx_outline_claim_status ON outline_claim(status);

-- ============================================================================
-- Research Exploration Log
-- ============================================================================
-- Tracks AI exploration steps for transparency and undo

CREATE TABLE IF NOT EXISTS exploration_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES research_session(id) ON DELETE CASCADE,
    
    action_type TEXT NOT NULL
        CHECK (action_type IN ('search', 'ingest', 'summarize', 'cluster', 
                               'generate_outline', 'expand', 'user_feedback')),
    
    -- What triggered this action
    trigger TEXT,  -- 'auto', 'user_request', 'critique_response'
    user_input TEXT,  -- User's message if applicable
    
    -- What happened
    description TEXT NOT NULL,
    details JSONB,  -- Action-specific details
    
    -- Results
    nodes_created INTEGER DEFAULT 0,
    sources_ingested INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_exploration_log_session ON exploration_log(session_id);
CREATE INDEX idx_exploration_log_type ON exploration_log(action_type);

-- ============================================================================
-- Helper function: Update research_session stats
-- ============================================================================

CREATE OR REPLACE FUNCTION update_research_session_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE research_session
    SET 
        nodes_created = (
            SELECT COUNT(*) FROM knowledge_node 
            WHERE session_id = COALESCE(NEW.session_id, OLD.session_id)
        ),
        sources_ingested = (
            SELECT COUNT(DISTINCT source_id) FROM knowledge_node 
            WHERE session_id = COALESCE(NEW.session_id, OLD.session_id)
            AND source_id IS NOT NULL
        ),
        updated_at = NOW()
    WHERE id = COALESCE(NEW.session_id, OLD.session_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_session_stats
AFTER INSERT OR UPDATE OR DELETE ON knowledge_node
FOR EACH ROW
EXECUTE FUNCTION update_research_session_stats();

-- ============================================================================
-- Helper function: Update claim source count
-- ============================================================================

CREATE OR REPLACE FUNCTION update_claim_source_count()
RETURNS TRIGGER AS $$
BEGIN
    NEW.source_count := array_length(NEW.supporting_nodes, 1);
    IF NEW.source_count IS NULL THEN
        NEW.source_count := 0;
    END IF;
    
    -- Auto-assess evidence strength based on source count
    IF NEW.source_count = 0 THEN
        NEW.evidence_strength := 'none';
    ELSIF NEW.source_count = 1 THEN
        NEW.evidence_strength := 'weak';
    ELSIF NEW.source_count <= 3 THEN
        NEW.evidence_strength := 'moderate';
    ELSE
        NEW.evidence_strength := 'strong';
    END IF;
    
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_claim_sources
BEFORE INSERT OR UPDATE OF supporting_nodes ON outline_claim
FOR EACH ROW
EXECUTE FUNCTION update_claim_source_count();

