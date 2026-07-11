-- Product-feed intelligence: import e-commerce catalogs, find listing issues
-- at SKU scale, AI-optimize titles/descriptions, export a supplemental feed.

CREATE TABLE IF NOT EXISTS product_feeds (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name VARCHAR(255),
  source_type VARCHAR(20) DEFAULT 'csv', -- csv, url (Google Merchant XML/CSV)
  source_url VARCHAR(1000),
  product_count INT DEFAULT 0,
  issue_count INT DEFAULT 0,
  optimized_count INT DEFAULT 0,
  truncated BOOLEAN DEFAULT FALSE, -- feed larger than the import cap
  status VARCHAR(20) DEFAULT 'ready', -- importing, ready, failed
  last_imported TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_product_feeds_project_id ON product_feeds(project_id);

CREATE TABLE IF NOT EXISTS feed_products (
  id BIGSERIAL PRIMARY KEY,
  feed_id BIGINT NOT NULL REFERENCES product_feeds(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  product_key VARCHAR(255) NOT NULL, -- the feed's product id / SKU
  title VARCHAR(1000),
  description TEXT,
  brand VARCHAR(255),
  category VARCHAR(500),
  price VARCHAR(100),
  link VARCHAR(1000),
  availability VARCHAR(50),
  issues JSONB, -- [{type, severity, detail}]
  issue_count INT DEFAULT 0,
  optimized_title VARCHAR(1000),
  optimized_description TEXT,
  optimization_status VARCHAR(20) DEFAULT 'pending', -- pending, optimized, approved
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(feed_id, product_key)
);

CREATE INDEX idx_feed_products_feed_id ON feed_products(feed_id);
CREATE INDEX idx_feed_products_project_id ON feed_products(project_id);
CREATE INDEX idx_feed_products_issue_count ON feed_products(issue_count DESC);
CREATE INDEX idx_feed_products_opt_status ON feed_products(optimization_status);

-- RLS
ALTER TABLE product_feeds ENABLE ROW LEVEL SECURITY;
ALTER TABLE feed_products ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own project feeds"
  ON product_feeds FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );

CREATE POLICY "Users can view own project feed products"
  ON feed_products FOR SELECT
  USING (
    project_id IN (
      SELECT id FROM projects WHERE auth.uid() = ANY(owner_user_ids)
    )
  );
