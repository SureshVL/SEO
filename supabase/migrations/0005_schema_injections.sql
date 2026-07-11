-- Schema injection tracking and batch operations
-- Stores details about each schema injection attempt, status, and errors

create table if not exists schema_injections (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  batch_id uuid not null default gen_random_uuid(), -- group multiple URLs in one operation

  url text not null,
  cms_platform text, -- detected: wordpress, shopify, webflow, custom, unknown
  schema_type text not null, -- FAQ, Product, Organization, LocalBusiness, etc.

  status text not null default 'pending', -- pending, injected, failed, skipped
  error_message text,

  request_body jsonb, -- full schema JSON-LD being injected
  response_body jsonb, -- CMS response (API response or HTML after injection)

  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  attempted_at timestamp with time zone
);

create index idx_schema_injections_project on schema_injections(project_id);
create index idx_schema_injections_batch on schema_injections(batch_id);
create index idx_schema_injections_status on schema_injections(status);
create index idx_schema_injections_created on schema_injections(created_at desc);

-- Batch injection job metadata
create table if not exists schema_injection_jobs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,

  job_id text unique not null, -- "inj_" + nanoid for tracking
  status text not null default 'queued', -- queued, running, completed, failed
  error_message text,

  total_urls int not null,
  processed_count int not null default 0,
  success_count int not null default 0,
  failure_count int not null default 0,

  schema_types jsonb not null, -- array of schema types to inject per URL
  cms_auto_detect boolean not null default true,

  created_at timestamp with time zone not null default now(),
  started_at timestamp with time zone,
  completed_at timestamp with time zone
);

create index idx_schema_injection_jobs_project on schema_injection_jobs(project_id);
create index idx_schema_injection_jobs_status on schema_injection_jobs(status);
create index idx_schema_injection_jobs_created on schema_injection_jobs(created_at desc);

-- CMS credentials per project (for WordPress, Shopify, etc.)
create table if not exists cms_credentials (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null unique references projects(id) on delete cascade,

  cms_platform text not null, -- wordpress, shopify, webflow, custom

  endpoint_url text, -- e.g., https://mysite.com/wp-json for WordPress
  api_key text, -- encrypted via PG encrypt extension or app-side
  api_secret text, -- encrypted

  auth_token text, -- encrypted bearer token or oauth2 token

  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now()
);

create index idx_cms_credentials_project on cms_credentials(project_id);
create index idx_cms_credentials_platform on cms_credentials(cms_platform);
