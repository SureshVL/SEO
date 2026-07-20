-- OMNI-RANK — Migration 0021: backfill orgs for pre-existing auth users
--
-- The handle_new_user() trigger (migration 0002) provisions an org + user
-- profile + credits ONLY when a new row is inserted into auth.users. Users
-- who were created BEFORE that trigger existed (e.g. during local dev) have
-- an auth identity but no public.users row and no org, so every org-scoped
-- API call 403s with "User is not attached to an organization".
--
-- This migration is fully idempotent — safe to run any number of times.
-- It (1) re-asserts the trigger so future signups always provision, and
-- (2) backfills anyone currently missing an org.

-- 1. Re-assert the provisioning trigger (create-or-replace is idempotent) ----
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
as $$
declare
    new_org_id uuid;
begin
    insert into public.organizations (name, slug)
    values (
        coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1)),
        replace(lower(split_part(new.email, '@', 1)), '.', '-') || '-' || substr(gen_random_uuid()::text, 1, 8)
    )
    returning id into new_org_id;

    insert into public.users (id, email, full_name, avatar_url, org_id, role)
    values (
        new.id,
        new.email,
        coalesce(new.raw_user_meta_data->>'full_name', ''),
        coalesce(new.raw_user_meta_data->>'avatar_url', ''),
        new_org_id,
        'owner'
    );

    insert into public.credit_balances (org_id, credits_remaining)
    values (new_org_id, 10)
    on conflict do nothing;

    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- 2a. Backfill auth users that have NO public.users row at all ---------------
do $$
declare
    u record;
    new_org_id uuid;
begin
    for u in
        select au.id, au.email, au.raw_user_meta_data as meta
        from auth.users au
        left join public.users pu on pu.id = au.id
        where pu.id is null and au.email is not null
    loop
        insert into public.organizations (name, slug)
        values (
            coalesce(u.meta->>'full_name', split_part(u.email, '@', 1)),
            replace(lower(split_part(u.email, '@', 1)), '.', '-') || '-' || substr(gen_random_uuid()::text, 1, 8)
        )
        returning id into new_org_id;

        insert into public.users (id, email, full_name, avatar_url, org_id, role)
        values (
            u.id, u.email,
            coalesce(u.meta->>'full_name', ''),
            coalesce(u.meta->>'avatar_url', ''),
            new_org_id, 'owner'
        );

        insert into public.credit_balances (org_id, credits_remaining)
        values (new_org_id, 10) on conflict do nothing;
    end loop;
end $$;

-- 2b. Backfill public.users rows that exist but have a NULL org -------------
do $$
declare
    u record;
    new_org_id uuid;
begin
    for u in select id, email from public.users where org_id is null and email is not null loop
        insert into public.organizations (name, slug)
        values (
            split_part(u.email, '@', 1),
            replace(lower(split_part(u.email, '@', 1)), '.', '-') || '-' || substr(gen_random_uuid()::text, 1, 8)
        )
        returning id into new_org_id;

        update public.users set org_id = new_org_id where id = u.id;

        insert into public.credit_balances (org_id, credits_remaining)
        values (new_org_id, 10) on conflict do nothing;
    end loop;
end $$;
