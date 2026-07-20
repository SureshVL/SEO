-- Competitor analysis and outrank strategy generation
-- Tables: competitors, competitor_analysis, outrank_strategies

CREATE TABLE IF NOT EXISTS competitors (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  domain VARCHAR(255) NOT NULL,
  name VARCHAR(255),
  tld VARCHAR(10),
  country_code VARCHAR(2),
  language_code VARCHAR(2),
  added_at TIMESTAMP DEFAULT NOW(),
  last_analyzed TIMESTAMP,
  UNIQUE(project_id, domain)
);

CREATE INDEX idx_competitors_project_id ON competitors(project_id);
CREATE INDEX idx_competitors_domain ON competitors(domain);

CREATE TABLE IF NOT EXISTS competitor_analysis (
  id BIGSERIAL PRIMARY KEY,
  competitor_id BIGINT NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  analysis_type VARCHAR(50), -- seo_overview, top_keywords, backlinks, content_strategy, technical
  keyword_count INT,
  top_keywords JSONB, -- array of {keyword, volume, position, url}
  content_count INT,
  avg_content_length INT,
  backlink_count INT,
  referring_domains INT,
  top_pages JSONB, -- array of {url, traffic_est, keywords}
  technical_score INT,
  issues JSONB, -- array of {issue_type, count}
  full_analysis JSONB, -- complete analysis data
  ai_insights TEXT, -- Claude-generated insights
  analyzed_at TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_analysis_competitor_id ON competitor_analysis(competitor_id);
CREATE INDEX idx_analysis_project_id ON competitor_analysis(project_id);
CREATE INDEX idx_analysis_type ON competitor_analysis(analysis_type);

CREATE TABLE IF NOT EXISTS outrank_strategies (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  competitor_id BIGINT NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
  strategy_type VARCHAR(50), -- content, keywords, technical, backlinks
  target_keyword VARCHAR(255),
  competitor_position INT,
  current_position INT,
  recommended_action TEXT,
  implementation_steps JSONB, -- array of action items
  content_gap JSONB, -- {topics_missing, format_opportunities, length_gap}
  estimated_roi TEXT,
  priority INT DEFAULT 0, -- higher = more important
  status VARCHAR(50) DEFAULT 'pending', -- pending, in_progress, completed
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_strategies_project_id ON outrank_strategies(project_id);
CREATE INDEX idx_strategies_competitor_id ON outrank_strategies(competitor_id);
CREATE INDEX idx_strategies_status ON outrank_strategies(status);
CREATE INDEX idx_strategies_priority ON outrank_strategies(priority DESC);

-- RLS Policies
ALTER TABLE competitors ENABLE ROW LEVEL SECURITY;
ALTER TABLE competitor_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE outrank_strategies ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own project competitors"
  ON competitors FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert competitors for own projects"
  ON competitors FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can delete competitors in own projects"
  ON competitors FOR DELETE
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project analysis"
  ON competitor_analysis FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert competitor analysis for own projects"
  ON competitor_analysis FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project strategies"
  ON outrank_strategies FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert strategies for own projects"
  ON outrank_strategies FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can update strategies in own projects"
  ON outrank_strategies FOR UPDATE
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );
