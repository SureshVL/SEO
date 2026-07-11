-- Server-side storage for Google OAuth tokens (GA4 / GSC).
-- Previously access tokens lived in the browser's localStorage (XSS-stealable)
-- and were sent on every analytics call. Now they are held encrypted server-side.

CREATE TABLE IF NOT EXISTS oauth_tokens (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  service VARCHAR(20) NOT NULL,       -- ga4, gsc
  access_token TEXT NOT NULL,         -- encrypted (secrets_crypto)
  refresh_token TEXT,                 -- encrypted
  expires_at TIMESTAMP,               -- access-token expiry
  email VARCHAR(255),
  updated_at TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, service)
);

CREATE INDEX idx_oauth_tokens_project ON oauth_tokens(project_id);

-- service-role only (tokens must never be client-readable); deny-by-default RLS
ALTER TABLE oauth_tokens ENABLE ROW LEVEL SECURITY;
