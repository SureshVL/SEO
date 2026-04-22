-- Link-building prospect tracker + outreach pipeline.
-- Each row represents a target domain/page we want a backlink from.

create table if not exists public.link_prospects (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    domain text not null,
    url text,
    contact_name text,
    contact_email text,
    domain_rating float,
    referring_domains int,
    status text not null default 'new'
        check (status in ('new','researching','contacted','replied','agreed','placed','declined')),
    template text,
    subject text,
    notes text,
    opportunity_score float,
    already_linking boolean not null default false,
    outreach_sent_at timestamptz,
    response_at timestamptz,
    placed_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_link_prospects_project on public.link_prospects(project_id, status);
create index if not exists idx_link_prospects_domain on public.link_prospects(domain);
