-- Autopilot technical audits - continuous monitoring for SEO issues
-- Tables: audit_schedules, audit_runs, audit_issues, issue_resolutions

CREATE TABLE IF NOT EXISTS audit_schedules (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  audit_type VARCHAR(50), -- full_site, crawl_errors, broken_links, schema, performance
  frequency VARCHAR(50) DEFAULT 'weekly', -- daily, weekly, monthly, on_demand
  enabled BOOLEAN DEFAULT TRUE,
  last_run TIMESTAMP,
  next_run TIMESTAMP,
  config JSONB, -- audit-specific configuration
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, audit_type)
);

CREATE INDEX idx_audit_schedules_project_id ON audit_schedules(project_id);
CREATE INDEX idx_audit_schedules_next_run ON audit_schedules(next_run);
CREATE INDEX idx_audit_schedules_enabled ON audit_schedules(enabled);

CREATE TABLE IF NOT EXISTS audit_runs (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  audit_type VARCHAR(50),
  status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  total_pages_checked INT DEFAULT 0,
  issues_found INT DEFAULT 0,
  critical_count INT DEFAULT 0,
  warning_count INT DEFAULT 0,
  summary TEXT, -- brief summary of findings
  result JSONB, -- detailed results/statistics
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_runs_project_id ON audit_runs(project_id);
CREATE INDEX idx_audit_runs_status ON audit_runs(status);
CREATE INDEX idx_audit_runs_created ON audit_runs(created_at DESC);

CREATE TABLE IF NOT EXISTS audit_issues (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  audit_run_id BIGINT REFERENCES audit_runs(id) ON DELETE CASCADE,
  issue_type VARCHAR(50), -- broken_link, orphan_page, crawl_error, missing_canonical, slow_load, schema_error, etc.
  severity VARCHAR(20), -- critical, warning, info
  affected_url VARCHAR(500),
  affected_element VARCHAR(500), -- element that caused the issue
  description TEXT, -- human-readable issue description
  recommendation TEXT, -- how to fix it
  evidence JSONB, -- supporting data (error codes, load times, etc.)
  status VARCHAR(50) DEFAULT 'open', -- open, in_progress, resolved, ignored
  assigned_to VARCHAR(255),
  first_detected TIMESTAMP,
  last_detected TIMESTAMP,
  resolved_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, issue_type, affected_url)
);

CREATE INDEX idx_audit_issues_project_id ON audit_issues(project_id);
CREATE INDEX idx_audit_issues_severity ON audit_issues(severity);
CREATE INDEX idx_audit_issues_status ON audit_issues(status);
CREATE INDEX idx_audit_issues_type ON audit_issues(issue_type);
CREATE INDEX idx_audit_issues_url ON audit_issues(affected_url);
CREATE INDEX idx_audit_issues_detected ON audit_issues(last_detected DESC);

CREATE TABLE IF NOT EXISTS issue_resolutions (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  issue_id BIGINT NOT NULL REFERENCES audit_issues(id) ON DELETE CASCADE,
  resolution_type VARCHAR(50), -- auto_fix, manual_fix, ignored, false_positive
  resolution_details TEXT, -- what was done
  resolved_by VARCHAR(255), -- who resolved it (user or "autopilot")
  verification_status VARCHAR(50) DEFAULT 'pending', -- pending, verified, needs_reverify
  verified_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_issue_resolutions_project_id ON issue_resolutions(project_id);
CREATE INDEX idx_issue_resolutions_issue_id ON issue_resolutions(issue_id);
CREATE INDEX idx_issue_resolutions_type ON issue_resolutions(resolution_type);

CREATE TABLE IF NOT EXISTS audit_performance_metrics (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  audit_run_id BIGINT REFERENCES audit_runs(id) ON DELETE CASCADE,
  url VARCHAR(500),
  load_time_ms NUMERIC, -- page load time in milliseconds
  core_web_vitals JSONB, -- LCP, FID, CLS scores
  mobile_friendly BOOLEAN,
  has_canonical BOOLEAN,
  has_meta_description BOOLEAN,
  has_h1 BOOLEAN,
  crawlable BOOLEAN,
  indexable BOOLEAN,
  redirects_count INT DEFAULT 0,
  internal_links INT DEFAULT 0,
  external_links INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_perf_metrics_project_id ON audit_performance_metrics(project_id);
CREATE INDEX idx_perf_metrics_url ON audit_performance_metrics(url);
CREATE INDEX idx_perf_metrics_audit_run ON audit_performance_metrics(audit_run_id);

-- RLS Policies

ALTER TABLE audit_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE issue_resolutions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_performance_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own project audit schedules"
  ON audit_schedules FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert audit schedules for own projects"
  ON audit_schedules FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can update audit schedules in own projects"
  ON audit_schedules FOR UPDATE
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project audit runs"
  ON audit_runs FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert audit runs for own projects"
  ON audit_runs FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project audit issues"
  ON audit_issues FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert audit issues for own projects"
  ON audit_issues FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can update audit issues in own projects"
  ON audit_issues FOR UPDATE
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project issue resolutions"
  ON issue_resolutions FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert issue resolutions for own projects"
  ON issue_resolutions FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project performance metrics"
  ON audit_performance_metrics FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can insert performance metrics for own projects"
  ON audit_performance_metrics FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );
