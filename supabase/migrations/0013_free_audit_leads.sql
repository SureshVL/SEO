-- Free instant audit funnel - leads captured from public audits

CREATE TABLE IF NOT EXISTS audit_leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) NOT NULL,
  domain VARCHAR(255) NOT NULL,
  status VARCHAR(50) DEFAULT 'queued', -- queued, crawling, completed, failed
  score INT,
  report JSONB, -- full audit report
  source VARCHAR(50) DEFAULT 'free_audit', -- free_audit, referral, campaign
  converted BOOLEAN DEFAULT FALSE, -- became a paying user
  converted_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_leads_email ON audit_leads(email);
CREATE INDEX idx_audit_leads_domain ON audit_leads(domain);
CREATE INDEX idx_audit_leads_created ON audit_leads(created_at DESC);
CREATE INDEX idx_audit_leads_converted ON audit_leads(converted);

-- Service-role access only (public endpoint writes via backend)
ALTER TABLE audit_leads ENABLE ROW LEVEL SECURITY;
