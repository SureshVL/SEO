-- WhatsApp Copilot: phone-number → project links.
-- Run in Supabase SQL editor after 002_full_feature_tables.sql.

create table if not exists whatsapp_links (
  phone       text primary key,           -- wa_id, e.g. 9198xxxxxxx
  project_id  uuid not null references projects(id) on delete cascade,
  created_at  timestamptz default now()
);
create index if not exists idx_whatsapp_links_project_id on whatsapp_links(project_id);
alter table whatsapp_links enable row level security;
