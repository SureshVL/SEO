-- Content calendar and publishing automation
-- Tables: content_calendar (scheduling), publishing_logs (audit trail)

CREATE TABLE IF NOT EXISTS content_calendar (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  article_id BIGINT, -- reference to bulk_content_articles if from bulk job
  job_id VARCHAR(24), -- bulk job reference
  title VARCHAR(500) NOT NULL,
  slug VARCHAR(500) NOT NULL,
  content_type VARCHAR(50) DEFAULT 'article', -- article, product, page
  body TEXT,
  meta_description TEXT,
  seo_tags JSONB, -- array of SEO tags
  variables_used JSONB, -- CSV row data if from bulk generation
  scheduled_date TIMESTAMP NOT NULL,
  publish_date TIMESTAMP, -- actual publish time
  status VARCHAR(50) DEFAULT 'scheduled', -- scheduled, draft, published, failed, cancelled
  cms_platform VARCHAR(50), -- wordpress, shopify, webflow, custom
  cms_post_id VARCHAR(255), -- external ID from CMS
  cms_url VARCHAR(500), -- published URL
  auto_publish BOOLEAN DEFAULT TRUE,
  auto_social_share BOOLEAN DEFAULT FALSE,
  social_platforms JSONB, -- ["twitter", "linkedin", "facebook"]
  internal_links JSONB, -- array of {anchor_text, target_slug}
  featured_image_url VARCHAR(500),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  published_at TIMESTAMP
);

CREATE INDEX idx_calendar_project_id ON content_calendar(project_id);
CREATE INDEX idx_calendar_scheduled_date ON content_calendar(scheduled_date);
CREATE INDEX idx_calendar_status ON content_calendar(status);
CREATE INDEX idx_calendar_cms_post_id ON content_calendar(cms_post_id);

CREATE TABLE IF NOT EXISTS publishing_logs (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  calendar_id BIGINT NOT NULL REFERENCES content_calendar(id) ON DELETE CASCADE,
  event_type VARCHAR(50), -- queued, started, success, failed, retry, cancelled
  cms_platform VARCHAR(50),
  http_status INT,
  error_message TEXT,
  response_data JSONB,
  retry_count INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_logs_calendar_id ON publishing_logs(calendar_id);
CREATE INDEX idx_logs_project_id ON publishing_logs(project_id);
CREATE INDEX idx_logs_event_type ON publishing_logs(event_type);
CREATE INDEX idx_logs_created_at ON publishing_logs(created_at DESC);

-- RLS Policies
ALTER TABLE content_calendar ENABLE ROW LEVEL SECURITY;
ALTER TABLE publishing_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own project calendar"
  ON content_calendar FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert calendar events for own projects"
  ON content_calendar FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can update calendar events in own projects"
  ON content_calendar FOR UPDATE
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can delete calendar events in own projects"
  ON content_calendar FOR DELETE
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project publishing logs"
  ON publishing_logs FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert publishing logs for own projects"
  ON publishing_logs FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );
