-- Git-based write-back: open pull requests with SEO fixes against the
-- client's repository (headless / JAMstack / static sites).

CREATE TABLE IF NOT EXISTS git_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  provider VARCHAR(20) DEFAULT 'github', -- github (gitlab/bitbucket later)
  repo_owner VARCHAR(255) NOT NULL,
  repo_name VARCHAR(255) NOT NULL,
  base_branch VARCHAR(255) DEFAULT 'main',
  access_token TEXT NOT NULL, -- fine-grained PAT; service-role access only
  enabled BOOLEAN DEFAULT TRUE,
  verified BOOLEAN DEFAULT FALSE, -- repo reachable with the token
  verified_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, repo_owner, repo_name)
);

CREATE INDEX idx_git_connections_project_id ON git_connections(project_id);

CREATE TABLE IF NOT EXISTS git_pull_requests (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  connection_id UUID NOT NULL REFERENCES git_connections(id) ON DELETE CASCADE,
  pr_number INT,
  pr_url VARCHAR(500),
  branch_name VARCHAR(255),
  title VARCHAR(500),
  description TEXT,
  fix_type VARCHAR(50), -- content, schema, meta, redirects, hreflang, other
  files JSONB, -- [{path, action}]
  status VARCHAR(20) DEFAULT 'open', -- open, merged, closed
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_git_prs_project_id ON git_pull_requests(project_id);
CREATE INDEX idx_git_prs_status ON git_pull_requests(status);

-- RLS: tokens must never be readable by client-side keys
ALTER TABLE git_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE git_pull_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own project pull requests"
  ON git_pull_requests FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );
-- note: intentionally NO select policy on git_connections for authenticated
-- users - only the backend (service role) may read tokens.
