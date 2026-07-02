-- Global multi-language SEO - manage translations, localization, and hreflang
-- Tables: languages, localized_content, hreflang_config, region_targeting

CREATE TABLE IF NOT EXISTS languages (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  language_code VARCHAR(10) NOT NULL, -- en, es, fr, de, etc.
  region_code VARCHAR(10), -- US, ES, FR, etc. (optional for region-specific variants)
  display_name VARCHAR(100), -- English, Spanish, French, etc.
  is_default BOOLEAN DEFAULT FALSE,
  is_enabled BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, language_code, region_code)
);

CREATE INDEX idx_languages_project_id ON languages(project_id);
CREATE INDEX idx_languages_enabled ON languages(is_enabled);

CREATE TABLE IF NOT EXISTS localized_content (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  language_id BIGINT NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
  source_url VARCHAR(500), -- original URL
  localized_url VARCHAR(500), -- translated/localized URL path
  source_content_id BIGINT REFERENCES content_drafts(id) ON DELETE SET NULL,
  title VARCHAR(500), -- translated title
  description VARCHAR(1000), -- translated meta description
  content_markdown TEXT, -- translated content
  keywords JSONB, -- localized keywords for this language
  translation_status VARCHAR(50) DEFAULT 'pending', -- pending, translating, completed, needs_review
  translation_model VARCHAR(50), -- claude, google_translate, custom
  needs_human_review BOOLEAN DEFAULT FALSE,
  translated_by VARCHAR(255), -- AI model or human translator
  translated_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, language_id, source_url)
);

CREATE INDEX idx_localized_content_project_id ON localized_content(project_id);
CREATE INDEX idx_localized_content_language_id ON localized_content(language_id);
CREATE INDEX idx_localized_content_status ON localized_content(translation_status);
CREATE INDEX idx_localized_content_url ON localized_content(localized_url);

CREATE TABLE IF NOT EXISTS hreflang_config (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  source_url VARCHAR(500) NOT NULL, -- base URL path
  source_language_id BIGINT REFERENCES languages(id) ON DELETE SET NULL,
  target_language_id BIGINT NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
  target_url VARCHAR(500) NOT NULL, -- translated URL
  relationship_type VARCHAR(50) DEFAULT 'translation', -- translation, regional_variant, alternate
  is_configured BOOLEAN DEFAULT FALSE,
  config_method VARCHAR(50), -- header, tag, sitemap
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, source_url, target_language_id)
);

CREATE INDEX idx_hreflang_project_id ON hreflang_config(project_id);
CREATE INDEX idx_hreflang_source_url ON hreflang_config(source_url);
CREATE INDEX idx_hreflang_target_language ON hreflang_config(target_language_id);

CREATE TABLE IF NOT EXISTS region_targeting (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  language_id BIGINT NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
  region_code VARCHAR(10) NOT NULL, -- US, GB, CA, AU, etc.
  region_name VARCHAR(100),
  target_keywords JSONB, -- region-specific keywords
  local_content_needed BOOLEAN DEFAULT FALSE,
  local_competitors JSONB, -- array of competitor domains for this region
  seo_priority INT DEFAULT 5, -- 1-10
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, language_id, region_code)
);

CREATE INDEX idx_region_targeting_project_id ON region_targeting(project_id);
CREATE INDEX idx_region_targeting_language_id ON region_targeting(language_id);
CREATE INDEX idx_region_targeting_priority ON region_targeting(seo_priority DESC);

CREATE TABLE IF NOT EXISTS translation_jobs (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  job_type VARCHAR(50), -- bulk_translate, localize_content, analyze_multilingual
  source_language_id BIGINT REFERENCES languages(id) ON DELETE SET NULL,
  target_language_id BIGINT NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
  content_count INT DEFAULT 0,
  translated_count INT DEFAULT 0,
  reviewed_count INT DEFAULT 0,
  status VARCHAR(50) DEFAULT 'queued', -- queued, processing, completed, failed
  result JSONB, -- storage for job result/analysis
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_translation_jobs_project_id ON translation_jobs(project_id);
CREATE INDEX idx_translation_jobs_status ON translation_jobs(status);
CREATE INDEX idx_translation_jobs_created ON translation_jobs(created_at DESC);

-- RLS Policies

ALTER TABLE languages ENABLE ROW LEVEL SECURITY;
ALTER TABLE localized_content ENABLE ROW LEVEL SECURITY;
ALTER TABLE hreflang_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE region_targeting ENABLE ROW LEVEL SECURITY;
ALTER TABLE translation_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own project languages"
  ON languages FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert languages for own projects"
  ON languages FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project localized content"
  ON localized_content FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert localized content for own projects"
  ON localized_content FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can update localized content in own projects"
  ON localized_content FOR UPDATE
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project hreflang config"
  ON hreflang_config FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert hreflang config for own projects"
  ON hreflang_config FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can update hreflang config in own projects"
  ON hreflang_config FOR UPDATE
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project region targeting"
  ON region_targeting FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert region targeting for own projects"
  ON region_targeting FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project translation jobs"
  ON translation_jobs FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert translation jobs for own projects"
  ON translation_jobs FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );
