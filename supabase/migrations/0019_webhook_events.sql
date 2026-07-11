-- Webhook idempotency: record processed provider event ids to reject replays.

CREATE TABLE IF NOT EXISTS webhook_events (
  id BIGSERIAL PRIMARY KEY,
  provider VARCHAR(20) NOT NULL,   -- razorpay, stripe
  event_id VARCHAR(255) NOT NULL,  -- provider's unique event/delivery id
  received_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(provider, event_id)
);

CREATE INDEX idx_webhook_events_received ON webhook_events(received_at DESC);

-- service-role only (webhooks run on the backend); deny-by-default under RLS
ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY;
