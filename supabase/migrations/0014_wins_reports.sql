-- Weekly wins reports - proof-of-value tracking per project

CREATE TABLE IF NOT EXISTS wins_reports (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  period_start TIMESTAMP NOT NULL,
  period_end TIMESTAMP NOT NULL,
  stats JSONB, -- counts of work done in the period
  value_inr INT DEFAULT 0, -- agency-equivalent value delivered
  value_usd INT DEFAULT 0,
  sent_to VARCHAR(255), -- email the report was sent to (null = not emailed)
  sent_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_wins_reports_project_id ON wins_reports(project_id);
CREATE INDEX idx_wins_reports_created ON wins_reports(created_at DESC);

ALTER TABLE wins_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own project wins reports"
  ON wins_reports FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );
