-- Migration: Add topic grouping to source table
-- Purpose: Enable Library tab with AI-detected topic grouping

-- Add topic field to source table for grouping
ALTER TABLE source ADD COLUMN IF NOT EXISTS topic VARCHAR(255);
ALTER TABLE source ADD COLUMN IF NOT EXISTS topic_confidence FLOAT DEFAULT 0;

-- Create index for topic queries (grouped by project and topic)
CREATE INDEX IF NOT EXISTS idx_source_topic ON source(project_id, topic);

-- Add is_ingested field to knowledge_node if not exists
-- This distinguishes Explore (candidates) from Library (ingested)
ALTER TABLE knowledge_node ADD COLUMN IF NOT EXISTS is_ingested BOOLEAN DEFAULT false;

-- Create index for ingestion status queries
CREATE INDEX IF NOT EXISTS idx_knowledge_node_ingested ON knowledge_node(project_id, is_ingested);

-- Comment explaining the tab structure:
-- Explore: knowledge_node WHERE is_ingested = false (candidates)
-- Library: source table (ingested papers, grouped by topic)
-- Knowledge Tree: knowledge_node WHERE is_ingested = true (graph view)
-- Outline: outline_claim + linked sources

