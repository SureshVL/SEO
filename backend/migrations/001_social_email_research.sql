-- Migration: social posts calendar, email subscribers, AI research reports
-- Run this in the Supabase SQL editor (or psql) before using:
--   * /social/* and /projects/{id}/social-posts endpoints
--   * /email/subscribe, /email/unsubscribe, /cron/* email endpoints
--   * /api/research/* endpoints

-- ── Social Media Studio (Phase 1) ─────────────────────────────────
create table if not exists social_posts (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  platform text not null check (platform in ('instagram','facebook','tiktok','youtube','linkedin')),
  topic text default '',
  caption text not null default '',
  hashtags jsonb not null default '[]',
  content_goal text default 'engagement',
  media_notes text default '',
  scheduled_date timestamptz,
  status text not null default 'draft'
    check (status in ('draft','pending_approval','revision_requested','approved','scheduled','published')),
  revision_count int not null default 0,
  revision_notes jsonb not null default '[]',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_social_posts_project on social_posts (project_id, scheduled_date);
create index if not exists idx_social_posts_status on social_posts (project_id, status);

-- ── Social monthly metrics (manual entry / CSV until platform APIs land) ──
create table if not exists social_metrics (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  platform text not null check (platform in ('instagram','facebook','tiktok','youtube','linkedin')),
  month text not null, -- 'YYYY-MM'
  reach bigint not null default 0,
  impressions bigint not null default 0,
  engagement bigint not null default 0, -- likes + comments + shares + saves
  followers bigint not null default 0,  -- end-of-month follower count
  website_clicks bigint not null default 0,
  whatsapp_clicks bigint not null default 0,
  enquiries bigint not null default 0,
  posts_published int not null default 0,
  notes text default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, platform, month)
);
create index if not exists idx_social_metrics_project on social_metrics (project_id, month);

-- ── Email subscribers (research report + nurture sequence) ────────
create table if not exists email_subscribers (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  vertical text default 'general',
  source text default 'research_report',
  subscribed_at timestamptz default now(),
  unsubscribed_at timestamptz,
  nurture_sequence int not null default 0,
  last_email_sent timestamptz,
  email_count int not null default 0
);
create index if not exists idx_email_subscribers_active on email_subscribers (unsubscribed_at);

-- ── AI research reports ───────────────────────────────────────────
-- JSON payload columns are text because the service layer json.dumps()/loads() them.
create table if not exists ai_research_reports (
  id uuid primary key default gen_random_uuid(),
  vertical text not null,
  month text not null,
  status text not null default 'draft' check (status in ('draft','published','archived')),
  key_findings text not null default '[]',
  ai_engines text not null default '[]',
  citations_analyzed int not null default 0,
  top_movers text not null default '[]',
  recommendations text not null default '[]',
  pdf_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (vertical, month)
);
create index if not exists idx_research_reports_vertical on ai_research_reports (vertical, status, created_at desc);
