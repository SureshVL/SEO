-- Instant keyword mapping - cluster keywords and assign to URLs
-- Tables: keywords, keyword_clusters, keyword_mappings, url_assignments

CREATE TABLE IF NOT EXISTS keywords (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  keyword VARCHAR(255) NOT NULL,
  search_volume INT DEFAULT 0,
  keyword_difficulty INT DEFAULT 0, -- 0-100
  search_intent VARCHAR(50), -- informational, navigational, commercial, transactional
  cpc FLOAT DEFAULT 0, -- cost per click for paid search
  trend VARCHAR(20), -- rising, stable, declining
  source VARCHAR(50), -- dataforseo, manual, imported
  added_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, keyword)
);

CREATE INDEX idx_keywords_project_id ON keywords(project_id);
CREATE INDEX idx_keywords_volume ON keywords(search_volume DESC);
CREATE INDEX idx_keywords_difficulty ON keywords(keyword_difficulty);

CREATE TABLE IF NOT EXISTS keyword_clusters (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  cluster_name VARCHAR(255),
  seed_keyword VARCHAR(255), -- main keyword in cluster
  keywords JSONB, -- array of keyword IDs in cluster
  intent VARCHAR(50), -- dominant intent
  volume INT, -- total volume of cluster
  difficulty INT, -- average difficulty
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_clusters_project_id ON keyword_clusters(project_id);
CREATE INDEX idx_clusters_volume ON keyword_clusters(volume DESC);

CREATE TABLE IF NOT EXISTS keyword_mappings (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  cluster_id BIGINT REFERENCES keyword_clusters(id) ON DELETE SET NULL,
  keyword_id BIGINT NOT NULL REFERENCES keywords(id) ON DELETE CASCADE,
  url VARCHAR(500),
  relevance_score FLOAT, -- 0-1, how well URL matches keyword
  ranking_position INT, -- current position in SERP
  recommendation VARCHAR(50), -- target, optimize, create_new, better_match
  priority INT DEFAULT 5, -- 1-10, importance for implementation
  status VARCHAR(50) DEFAULT 'pending', -- pending, optimized, ranked, abandoned
  last_checked TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, keyword_id, url)
);

CREATE INDEX idx_mappings_project_id ON keyword_mappings(project_id);
CREATE INDEX idx_mappings_cluster_id ON keyword_mappings(cluster_id);
CREATE INDEX idx_mappings_url ON keyword_mappings(url);
CREATE INDEX idx_mappings_status ON keyword_mappings(status);
CREATE INDEX idx_mappings_priority ON keyword_mappings(priority DESC);

CREATE TABLE IF NOT EXISTS url_assignments (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  url VARCHAR(500) NOT NULL,
  title VARCHAR(500),
  assigned_keywords JSONB, -- array of keyword objects {keyword, cluster_id, priority}
  primary_keyword VARCHAR(255),
  secondary_keywords JSONB, -- array of secondary keywords
  target_volume INT, -- sum of keyword volumes
  optimization_score INT, -- 0-100, how well optimized
  content_gaps JSONB, -- array of missing topics/keywords
  recommendations TEXT,
  last_optimized TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, url)
);

CREATE INDEX idx_assignments_project_id ON url_assignments(project_id);
CREATE INDEX idx_assignments_url ON url_assignments(url);
CREATE INDEX idx_assignments_score ON url_assignments(optimization_score DESC);

CREATE TABLE IF NOT EXISTS keyword_gaps (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  keyword_id BIGINT NOT NULL REFERENCES keywords(id) ON DELETE CASCADE,
  cluster_id BIGINT REFERENCES keyword_clusters(id),
  gap_type VARCHAR(50), -- no_url_assigned, no_ranking, poor_match, orphan_keyword
  volume INT,
  difficulty INT,
  recommendation TEXT,
  priority INT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_gaps_project_id ON keyword_gaps(project_id);
CREATE INDEX idx_gaps_gap_type ON keyword_gaps(gap_type);
CREATE INDEX idx_gaps_priority ON keyword_gaps(priority DESC);

-- RLS Policies
ALTER TABLE keywords ENABLE ROW LEVEL SECURITY;
ALTER TABLE keyword_clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE keyword_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE url_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE keyword_gaps ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own project keywords"
  ON keywords FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert keywords for own projects"
  ON keywords FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project clusters"
  ON keyword_clusters FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert clusters for own projects"
  ON keyword_clusters FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project mappings"
  ON keyword_mappings FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert mappings for own projects"
  ON keyword_mappings FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can update mappings in own projects"
  ON keyword_mappings FOR UPDATE
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project assignments"
  ON url_assignments FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert assignments for own projects"
  ON url_assignments FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project gaps"
  ON keyword_gaps FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert gaps for own projects"
  ON keyword_gaps FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );
