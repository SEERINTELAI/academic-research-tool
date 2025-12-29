-- Migration: 006_report_table
-- Description: Add report table for storing generated papers

CREATE TABLE IF NOT EXISTS report (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    
    -- Content
    content TEXT NOT NULL,
    bibliography TEXT,
    
    -- Metadata
    citation_style TEXT DEFAULT 'apa',
    word_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Ensure one report per project (can be updated)
    CONSTRAINT unique_project_report UNIQUE (project_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_report_project_id ON report(project_id);

-- Trigger for updated_at
CREATE OR REPLACE TRIGGER update_report_timestamp
    BEFORE UPDATE ON report
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE report IS 'Generated paper reports from outline and sources';
COMMENT ON COLUMN report.content IS 'Full markdown content of the generated paper';
COMMENT ON COLUMN report.bibliography IS 'Formatted bibliography/references section';
COMMENT ON COLUMN report.citation_style IS 'Citation format used (apa, mla, chicago, ieee)';

