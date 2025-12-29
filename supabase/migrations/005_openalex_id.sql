-- Migration: 005_openalex_id
-- Description: Add openalex_id column to source table for proper API ID storage
-- 
-- The semantic_scholar_id column was incorrectly storing OpenAlex IDs.
-- This migration adds a dedicated openalex_id column and keeps semantic_scholar_id
-- for actual Semantic Scholar paper IDs.

-- Add openalex_id column
ALTER TABLE source ADD COLUMN IF NOT EXISTS openalex_id TEXT;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_source_openalex_id ON source(openalex_id);

-- Add comment
COMMENT ON COLUMN source.openalex_id IS 'OpenAlex work ID (e.g., W4214950786)';
COMMENT ON COLUMN source.semantic_scholar_id IS 'Semantic Scholar paper ID (40-char hex)';

