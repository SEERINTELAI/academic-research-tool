-- Migration: Add Chat Messages for Research UI
-- Created: 2024-12-29
-- Description: Chat message history and display_index for paper referencing

-- ============================================================================
-- Chat Messages
-- ============================================================================
-- Stores conversation history between user and AI during research

CREATE TABLE IF NOT EXISTS chat_message (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES research_session(id) ON DELETE CASCADE,
    
    -- Message content
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    
    -- Metadata for AI actions and references
    metadata JSONB DEFAULT '{}',
    -- Example metadata:
    -- {
    --   "action_taken": "search",
    --   "papers_added": [1, 2, 3],
    --   "papers_referenced": [5, 7],
    --   "intent": {"type": "search", "query": "quantum cryptography"}
    -- }
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_message_session ON chat_message(session_id);
CREATE INDEX idx_chat_message_created ON chat_message(session_id, created_at);

-- ============================================================================
-- Add display_index to knowledge_node
-- ============================================================================
-- Used for referencing papers by index in Explore tab (e.g., "paper #5")

ALTER TABLE knowledge_node 
ADD COLUMN IF NOT EXISTS display_index INTEGER;

-- Create index for efficient lookups by display_index
CREATE INDEX IF NOT EXISTS idx_knowledge_node_display_index 
ON knowledge_node(session_id, display_index) 
WHERE display_index IS NOT NULL;

-- ============================================================================
-- Auto-assign display_index for source nodes
-- ============================================================================
-- When a source node is created, assign the next available display_index

CREATE OR REPLACE FUNCTION assign_display_index()
RETURNS TRIGGER AS $$
BEGIN
    -- Only assign display_index for source-type nodes
    IF NEW.node_type = 'source' AND NEW.display_index IS NULL THEN
        SELECT COALESCE(MAX(display_index), 0) + 1 INTO NEW.display_index
        FROM knowledge_node
        WHERE session_id = NEW.session_id
        AND node_type = 'source';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_assign_display_index
BEFORE INSERT ON knowledge_node
FOR EACH ROW
EXECUTE FUNCTION assign_display_index();

