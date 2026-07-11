-- Edge snippet injection - deploy SEO fixes to ANY website via a single <script> tag
-- Works on custom-built sites, e-commerce platforms, legacy stacks: no CMS API needed.

CREATE TABLE IF NOT EXISTS edge_sites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  domain VARCHAR(255) NOT NULL,
  site_token VARCHAR(64) NOT NULL UNIQUE, -- public token embedded in the snippet
  enabled BOOLEAN DEFAULT TRUE,
  verified BOOLEAN DEFAULT FALSE, -- snippet detected on the live site
  verified_at TIMESTAMP,
  last_seen_at TIMESTAMP, -- last config fetch from the snippet
  settings JSONB, -- allowed rule types etc.
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, domain)
);

CREATE INDEX idx_edge_sites_project_id ON edge_sites(project_id);
CREATE INDEX idx_edge_sites_token ON edge_sites(site_token);

CREATE TABLE IF NOT EXISTS edge_rules (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  site_id UUID NOT NULL REFERENCES edge_sites(id) ON DELETE CASCADE,
  url_pattern VARCHAR(500) NOT NULL, -- path to match ('*' = site-wide)
  match_type VARCHAR(20) DEFAULT 'exact', -- exact, prefix, contains, all
  rule_type VARCHAR(50) NOT NULL, -- schema, title, meta_description, canonical, hreflang, meta
  payload JSONB NOT NULL, -- rule-type-specific content
  enabled BOOLEAN DEFAULT TRUE,
  priority INT DEFAULT 5,
  source VARCHAR(50) DEFAULT 'manual', -- manual, audit_fix, schema_feature, multilingual
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_edge_rules_project_id ON edge_rules(project_id);
CREATE INDEX idx_edge_rules_site_id ON edge_rules(site_id);
CREATE INDEX idx_edge_rules_enabled ON edge_rules(enabled);

-- RLS
ALTER TABLE edge_sites ENABLE ROW LEVEL SECURITY;
ALTER TABLE edge_rules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own project edge sites"
  ON edge_sites FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can manage edge sites for own projects"
  ON edge_sites FOR ALL
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project edge rules"
  ON edge_rules FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can manage edge rules for own projects"
  ON edge_rules FOR ALL
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );
