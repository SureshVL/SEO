-- OMNI-RANK OR-1 Core schema
create extension if not exists vector;

create table if not exists public.projects (
    id uuid primary key default gen_random_uuid(),
    client_url text not null,
    target_niche text,
    current_rankings jsonb not null default '{}'::jsonb,
    goal_keywords text[] not null default '{}',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.competitor_intel (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    source_url text not null,
    scraped_content text,
    backlink_profiles jsonb not null default '{}'::jsonb,
    entity_maps jsonb not null default '{}'::jsonb,
    embedding vector(1536),
    captured_at timestamptz not null default now()
);

create table if not exists public.agent_logs (
    id bigint generated always as identity primary key,
    project_id uuid not null references public.projects(id) on delete cascade,
    agent_name text not null,
    action_type text not null,
    action_payload jsonb not null default '{}'::jsonb,
    status text not null default 'ok',
    created_at timestamptz not null default now()
);

create table if not exists public.content_queue (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    content_type text not null,
    title text not null,
    slug text,
    body_markdown text not null,
    target_keyword text,
    publish_target text,
    queue_status text not null default 'draft',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_projects_client_url on public.projects (client_url);
create index if not exists idx_competitor_project on public.competitor_intel (project_id);
create index if not exists idx_agent_logs_project_created on public.agent_logs (project_id, created_at desc);
create index if not exists idx_content_queue_project_status on public.content_queue (project_id, queue_status);

-- optional vector similarity index (requires enough rows before useful)
create index if not exists idx_competitor_intel_embedding
on public.competitor_intel
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);
