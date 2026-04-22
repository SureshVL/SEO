-- Monthly workflow run history
-- Records each execution of the Week 1-4 SEO cadence for auditing
-- and surfacing "last run X days ago" in the dashboard.

create table if not exists public.workflow_runs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  week smallint not null check (week between 1 and 4),
  week_label text not null,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  completed smallint not null default 0,
  skipped smallint not null default 0,
  failed smallint not null default 0,
  tasks jsonb not null default '[]'::jsonb,  -- [{name, status, detail, data}]
  triggered_by text not null default 'cron', -- 'cron' | 'manual'
  created_at timestamptz not null default now()
);

create index if not exists workflow_runs_project_idx
  on public.workflow_runs (project_id, started_at desc);

create index if not exists workflow_runs_week_idx
  on public.workflow_runs (project_id, week, started_at desc);
