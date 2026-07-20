-- Bulk content generation at scale
-- Tables: bulk_content_jobs, bulk_content_articles

CREATE TABLE IF NOT EXISTS bulk_content_jobs (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  job_id VARCHAR(24) NOT NULL UNIQUE,
  status VARCHAR(50) DEFAULT 'queued', -- queued, running, completed, failed, cancelled
  total_articles INT DEFAULT 0,
  completed_articles INT DEFAULT 0,
  failed_articles INT DEFAULT 0,
  template_name VARCHAR(255),
  template_data JSONB,
  enhance_with_ai BOOLEAN DEFAULT TRUE,
  export_format VARCHAR(20) DEFAULT 'json', -- json, csv, markdown
  export_data TEXT, -- serialized export (JSON, CSV, Markdown)
  export_url VARCHAR(1024), -- S3 or download link
  schedule_publish TIMESTAMP,
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_bulk_jobs_project_id ON bulk_content_jobs(project_id);
CREATE INDEX idx_bulk_jobs_job_id ON bulk_content_jobs(job_id);
CREATE INDEX idx_bulk_jobs_status ON bulk_content_jobs(status);
CREATE INDEX idx_bulk_jobs_created_at ON bulk_content_jobs(created_at DESC);

CREATE TABLE IF NOT EXISTS bulk_content_articles (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  job_id VARCHAR(24) NOT NULL,
  slug VARCHAR(500) NOT NULL,
  title VARCHAR(500),
  meta_description TEXT,
  h1 VARCHAR(500),
  body TEXT, -- Markdown content
  word_count INT DEFAULT 0,
  reading_time_minutes INT DEFAULT 0,
  variables_used JSONB, -- CSV row data used to generate
  ai_enhanced BOOLEAN DEFAULT FALSE,
  errors JSONB, -- array of error messages
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (job_id) REFERENCES bulk_content_jobs(job_id) ON DELETE CASCADE
);

CREATE INDEX idx_bulk_articles_project_id ON bulk_content_articles(project_id);
CREATE INDEX idx_bulk_articles_job_id ON bulk_content_articles(job_id);
CREATE INDEX idx_bulk_articles_created_at ON bulk_content_articles(created_at DESC);

-- RLS Policies
ALTER TABLE bulk_content_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE bulk_content_articles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own project bulk jobs"
  ON bulk_content_jobs FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert bulk jobs for own projects"
  ON bulk_content_jobs FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can update bulk jobs in own projects"
  ON bulk_content_jobs FOR UPDATE
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can delete bulk jobs in own projects"
  ON bulk_content_jobs FOR DELETE
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project bulk articles"
  ON bulk_content_articles FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert bulk articles for own projects"
  ON bulk_content_articles FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can update bulk articles in own projects"
  ON bulk_content_articles FOR UPDATE
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can delete bulk articles in own projects"
  ON bulk_content_articles FOR DELETE
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );
