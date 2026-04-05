-- OMNI-RANK OR-1 — Full Production Schema
-- Migration 0002: Users, Orgs, Billing, Keywords, Rank Tracking, RBAC, RLS

-- ============================================================
-- 1. ORGANIZATIONS & USERS
-- ============================================================

create table if not exists public.organizations (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    slug text not null unique,
    plan text not null default 'starter' check (plan in ('starter','growth','agency','enterprise')),
    plan_status text not null default 'active' check (plan_status in ('active','past_due','cancelled','trialing')),
    max_projects int not null default 1,
    max_keywords int not null default 50,
    max_reports_per_month int not null default 5,
    razorpay_customer_id text,
    razorpay_subscription_id text,
    trial_ends_at timestamptz,
    current_period_start timestamptz,
    current_period_end timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.users (
    id uuid primary key references auth.users(id) on delete cascade,
    email text not null unique,
    full_name text,
    avatar_url text,
    org_id uuid references public.organizations(id) on delete set null,
    role text not null default 'member' check (role in ('owner','admin','member','viewer')),
    onboarded boolean not null default false,
    last_login_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.org_invites (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references public.organizations(id) on delete cascade,
    email text not null,
    role text not null default 'member' check (role in ('admin','member','viewer')),
    invited_by uuid references public.users(id) on delete set null,
    accepted_at timestamptz,
    expires_at timestamptz not null default (now() + interval '7 days'),
    created_at timestamptz not null default now()
);

-- ============================================================
-- 2. ENHANCE PROJECTS TABLE (add org ownership)
-- ============================================================

alter table public.projects
    add column if not exists org_id uuid references public.organizations(id) on delete cascade,
    add column if not exists name text not null default 'Untitled Project',
    add column if not exists domain text,
    add column if not exists favicon_url text,
    add column if not exists settings jsonb not null default '{}'::jsonb,
    add column if not exists status text not null default 'active' check (status in ('active','paused','archived'));

create index if not exists idx_projects_org on public.projects(org_id);

-- ============================================================
-- 3. KEYWORDS & RANK TRACKING
-- ============================================================

create table if not exists public.keywords (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    keyword text not null,
    locale text not null default 'en-US',
    target_region text not null default 'IN',
    search_volume int,
    difficulty float,
    cpc_inr float,
    intent text check (intent in ('informational','navigational','transactional','commercial')),
    tags text[] not null default '{}',
    is_primary boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique(project_id, keyword, locale, target_region)
);

create table if not exists public.rank_history (
    id bigint generated always as identity primary key,
    keyword_id uuid not null references public.keywords(id) on delete cascade,
    position int,
    previous_position int,
    url text,
    serp_features text[] not null default '{}',
    search_volume int,
    checked_at timestamptz not null default now()
);

create index if not exists idx_rank_history_keyword_date on public.rank_history(keyword_id, checked_at desc);
create index if not exists idx_keywords_project on public.keywords(project_id);

-- ============================================================
-- 4. BACKLINK PROFILES
-- ============================================================

create table if not exists public.backlinks (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    source_url text not null,
    target_url text not null,
    anchor_text text,
    domain_authority float,
    is_dofollow boolean not null default true,
    first_seen_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),
    status text not null default 'active' check (status in ('active','lost','broken'))
);

create index if not exists idx_backlinks_project on public.backlinks(project_id);

-- ============================================================
-- 5. SITE AUDITS
-- ============================================================

create table if not exists public.site_audits (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    audit_type text not null check (audit_type in ('technical','content','performance','full')),
    status text not null default 'pending' check (status in ('pending','running','completed','failed')),
    score float,
    results jsonb not null default '{}'::jsonb,
    issues_found int not null default 0,
    issues_critical int not null default 0,
    issues_warning int not null default 0,
    lighthouse_data jsonb,
    started_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz not null default now()
);

create index if not exists idx_site_audits_project on public.site_audits(project_id, created_at desc);

-- ============================================================
-- 6. AI AGENT SESSIONS & REPORTS
-- ============================================================

create table if not exists public.agent_sessions (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    user_id uuid references public.users(id) on delete set null,
    agent_type text not null check (agent_type in ('research','content','technical','aso','strategy','chat')),
    status text not null default 'running' check (status in ('running','completed','failed','cancelled')),
    input_payload jsonb not null default '{}'::jsonb,
    output_payload jsonb,
    tokens_used int not null default 0,
    model_used text,
    cost_usd float not null default 0,
    duration_ms int,
    created_at timestamptz not null default now(),
    completed_at timestamptz
);

create table if not exists public.reports (
    id uuid primary key default gen_random_uuid(),
    project_id uuid not null references public.projects(id) on delete cascade,
    report_type text not null check (report_type in ('seo_audit','keyword_research','competitor_analysis','content_strategy','monthly_summary','custom')),
    title text not null,
    summary text,
    data jsonb not null default '{}'::jsonb,
    pdf_url text,
    is_white_label boolean not null default false,
    created_by uuid references public.users(id) on delete set null,
    created_at timestamptz not null default now()
);

create index if not exists idx_agent_sessions_project on public.agent_sessions(project_id, created_at desc);
create index if not exists idx_reports_project on public.reports(project_id, created_at desc);

-- ============================================================
-- 7. BILLING & USAGE METERING
-- ============================================================

create table if not exists public.billing_events (
    id bigint generated always as identity primary key,
    org_id uuid not null references public.organizations(id) on delete cascade,
    event_type text not null check (event_type in ('subscription_created','subscription_renewed','payment_success','payment_failed','plan_changed','credits_purchased','credits_used')),
    amount_inr int,  -- paise
    razorpay_payment_id text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.usage_metrics (
    id bigint generated always as identity primary key,
    org_id uuid not null references public.organizations(id) on delete cascade,
    metric_type text not null check (metric_type in ('api_call','ai_report','keyword_check','scrape','content_generation')),
    count int not null default 1,
    period_start date not null default current_date,
    period_end date not null default (current_date + interval '1 month'),
    created_at timestamptz not null default now()
);

create table if not exists public.credit_balances (
    org_id uuid primary key references public.organizations(id) on delete cascade,
    credits_remaining int not null default 0,
    credits_total_purchased int not null default 0,
    updated_at timestamptz not null default now()
);

create index if not exists idx_billing_events_org on public.billing_events(org_id, created_at desc);
create index if not exists idx_usage_metrics_org_period on public.usage_metrics(org_id, period_start);

-- ============================================================
-- 8. NOTIFICATIONS
-- ============================================================

create table if not exists public.notifications (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    type text not null check (type in ('rank_change','audit_complete','report_ready','billing','system','invite')),
    title text not null,
    body text,
    data jsonb not null default '{}'::jsonb,
    read boolean not null default false,
    created_at timestamptz not null default now()
);

create index if not exists idx_notifications_user on public.notifications(user_id, read, created_at desc);

-- ============================================================
-- 9. ROW LEVEL SECURITY POLICIES
-- ============================================================

alter table public.organizations enable row level security;
alter table public.users enable row level security;
alter table public.projects enable row level security;
alter table public.keywords enable row level security;
alter table public.rank_history enable row level security;
alter table public.backlinks enable row level security;
alter table public.site_audits enable row level security;
alter table public.agent_sessions enable row level security;
alter table public.reports enable row level security;
alter table public.content_queue enable row level security;
alter table public.competitor_intel enable row level security;
alter table public.agent_logs enable row level security;
alter table public.billing_events enable row level security;
alter table public.notifications enable row level security;

-- Helper: get current user's org_id
create or replace function public.get_user_org_id()
returns uuid
language sql
stable
security definer
as $$
  select org_id from public.users where id = auth.uid()
$$;

-- Users: can read/update own profile
create policy "users_select_own" on public.users for select using (id = auth.uid());
create policy "users_update_own" on public.users for update using (id = auth.uid());

-- Users: org members can see each other
create policy "users_select_org" on public.users for select
    using (org_id = public.get_user_org_id());

-- Organizations: members can read own org
create policy "orgs_select_member" on public.organizations for select
    using (id = public.get_user_org_id());

-- Organizations: only owner/admin can update
create policy "orgs_update_admin" on public.organizations for update
    using (
        id = public.get_user_org_id()
        and exists (
            select 1 from public.users
            where id = auth.uid() and role in ('owner','admin')
        )
    );

-- Projects: org members can read
create policy "projects_select_org" on public.projects for select
    using (org_id = public.get_user_org_id());

-- Projects: org admin/owner can insert/update/delete
create policy "projects_insert_org" on public.projects for insert
    with check (org_id = public.get_user_org_id());

create policy "projects_update_org" on public.projects for update
    using (org_id = public.get_user_org_id());

create policy "projects_delete_org" on public.projects for delete
    using (
        org_id = public.get_user_org_id()
        and exists (
            select 1 from public.users
            where id = auth.uid() and role in ('owner','admin')
        )
    );

-- Keywords, rank_history, backlinks, site_audits, agent_sessions, reports:
-- accessible if user's org owns the parent project
create policy "keywords_org" on public.keywords for all
    using (
        exists (
            select 1 from public.projects p
            where p.id = keywords.project_id and p.org_id = public.get_user_org_id()
        )
    );

create policy "rank_history_org" on public.rank_history for all
    using (
        exists (
            select 1 from public.keywords k
            join public.projects p on p.id = k.project_id
            where k.id = rank_history.keyword_id and p.org_id = public.get_user_org_id()
        )
    );

create policy "backlinks_org" on public.backlinks for all
    using (
        exists (
            select 1 from public.projects p
            where p.id = backlinks.project_id and p.org_id = public.get_user_org_id()
        )
    );

create policy "site_audits_org" on public.site_audits for all
    using (
        exists (
            select 1 from public.projects p
            where p.id = site_audits.project_id and p.org_id = public.get_user_org_id()
        )
    );

create policy "agent_sessions_org" on public.agent_sessions for all
    using (
        exists (
            select 1 from public.projects p
            where p.id = agent_sessions.project_id and p.org_id = public.get_user_org_id()
        )
    );

create policy "reports_org" on public.reports for all
    using (
        exists (
            select 1 from public.projects p
            where p.id = reports.project_id and p.org_id = public.get_user_org_id()
        )
    );

create policy "content_queue_org" on public.content_queue for all
    using (
        exists (
            select 1 from public.projects p
            where p.id = content_queue.project_id and p.org_id = public.get_user_org_id()
        )
    );

create policy "competitor_intel_org" on public.competitor_intel for all
    using (
        exists (
            select 1 from public.projects p
            where p.id = competitor_intel.project_id and p.org_id = public.get_user_org_id()
        )
    );

create policy "agent_logs_org" on public.agent_logs for all
    using (
        exists (
            select 1 from public.projects p
            where p.id = agent_logs.project_id and p.org_id = public.get_user_org_id()
        )
    );

-- Billing: org members can read, admin/owner can insert
create policy "billing_select_org" on public.billing_events for select
    using (org_id = public.get_user_org_id());

-- Notifications: own only
create policy "notifications_own" on public.notifications for all
    using (user_id = auth.uid());

-- ============================================================
-- 10. TRIGGERS: auto-update updated_at
-- ============================================================

create or replace function public.handle_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger set_updated_at before update on public.organizations
    for each row execute function public.handle_updated_at();

create trigger set_updated_at before update on public.users
    for each row execute function public.handle_updated_at();

create trigger set_updated_at before update on public.projects
    for each row execute function public.handle_updated_at();

create trigger set_updated_at before update on public.keywords
    for each row execute function public.handle_updated_at();

-- ============================================================
-- 11. TRIGGER: auto-create org + user on signup
-- ============================================================

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
as $$
declare
    new_org_id uuid;
begin
    -- Create a personal org for the new user
    insert into public.organizations (name, slug)
    values (
        coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1)),
        replace(lower(split_part(new.email, '@', 1)), '.', '-') || '-' || substr(gen_random_uuid()::text, 1, 8)
    )
    returning id into new_org_id;

    -- Create user profile
    insert into public.users (id, email, full_name, avatar_url, org_id, role)
    values (
        new.id,
        new.email,
        coalesce(new.raw_user_meta_data->>'full_name', ''),
        coalesce(new.raw_user_meta_data->>'avatar_url', ''),
        new_org_id,
        'owner'
    );

    -- Initialize credit balance
    insert into public.credit_balances (org_id, credits_remaining)
    values (new_org_id, 10);  -- 10 free credits on signup

    return new;
end;
$$;

create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();
