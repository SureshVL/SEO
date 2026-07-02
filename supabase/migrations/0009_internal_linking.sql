-- Smart internal linking and site structure analysis
-- Tables: site_pages, internal_link_opportunities, internal_links

CREATE TABLE IF NOT EXISTS site_pages (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  url VARCHAR(500) NOT NULL,
  slug VARCHAR(500),
  title VARCHAR(500),
  meta_description TEXT,
  h1 VARCHAR(500),
  content TEXT, -- page content/body
  word_count INT,
  topics JSONB, -- extracted keywords/topics from page
  internal_links_count INT DEFAULT 0,
  external_links_count INT DEFAULT 0,
  backlinks_count INT DEFAULT 0,
  crawled_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, url)
);

CREATE INDEX idx_pages_project_id ON site_pages(project_id);
CREATE INDEX idx_pages_url ON site_pages(url);
CREATE INDEX idx_pages_crawled_at ON site_pages(crawled_at DESC);

CREATE TABLE IF NOT EXISTS internal_link_opportunities (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  source_page_id BIGINT NOT NULL REFERENCES site_pages(id) ON DELETE CASCADE,
  target_page_id BIGINT NOT NULL REFERENCES site_pages(id) ON DELETE CASCADE,
  anchor_text VARCHAR(255),
  relevance_score FLOAT, -- 0-1, how relevant target is to source
  keyword_match VARCHAR(255), -- the keyword that matched
  linking_reason TEXT, -- why we think this link makes sense
  opportunity_type VARCHAR(50), -- keyword_relevant, semantic, topic_cluster, orphan_rescue
  priority INT DEFAULT 5, -- 1-10, higher = more important
  status VARCHAR(50) DEFAULT 'pending', -- pending, approved, implemented, rejected
  implemented_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, source_page_id, target_page_id)
);

CREATE INDEX idx_opportunities_project_id ON internal_link_opportunities(project_id);
CREATE INDEX idx_opportunities_source ON internal_link_opportunities(source_page_id);
CREATE INDEX idx_opportunities_target ON internal_link_opportunities(target_page_id);
CREATE INDEX idx_opportunities_status ON internal_link_opportunities(status);
CREATE INDEX idx_opportunities_priority ON internal_link_opportunities(priority DESC);

CREATE TABLE IF NOT EXISTS internal_links (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  source_page_id BIGINT NOT NULL REFERENCES site_pages(id) ON DELETE CASCADE,
  target_page_id BIGINT NOT NULL REFERENCES site_pages(id) ON DELETE CASCADE,
  anchor_text VARCHAR(255),
  link_position VARCHAR(50), -- beginning, middle, end
  implementation_method VARCHAR(50), -- manual, cms_api, webhook
  implemented_by VARCHAR(255),
  implemented_at TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, source_page_id, target_page_id, anchor_text)
);

CREATE INDEX idx_links_project_id ON internal_links(project_id);
CREATE INDEX idx_links_source ON internal_links(source_page_id);
CREATE INDEX idx_links_target ON internal_links(target_page_id);
CREATE INDEX idx_links_implemented ON internal_links(implemented_at DESC);

CREATE TABLE IF NOT EXISTS link_audit (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  page_id BIGINT REFERENCES site_pages(id) ON DELETE CASCADE,
  issue_type VARCHAR(50), -- orphan_page, broken_link, chains_too_long, no_internal_links
  severity VARCHAR(20), -- critical, high, medium, low
  affected_pages INT,
  recommendation TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_project_id ON link_audit(project_id);
CREATE INDEX idx_audit_issue_type ON link_audit(issue_type);

-- RLS Policies
ALTER TABLE site_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE internal_link_opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE internal_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE link_audit ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own project pages"
  ON site_pages FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert pages for own projects"
  ON site_pages FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can update pages in own projects"
  ON site_pages FOR UPDATE
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project opportunities"
  ON internal_link_opportunities FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert opportunities for own projects"
  ON internal_link_opportunities FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can update opportunities in own projects"
  ON internal_link_opportunities FOR UPDATE
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project links"
  ON internal_links FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert links for own projects"
  ON internal_links FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project audit"
  ON link_audit FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert audit records for own projects"
  ON link_audit FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );
