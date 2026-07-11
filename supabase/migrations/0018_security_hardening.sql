-- Security hardening: close RLS gaps found in the pre-launch audit.
-- Tables that had RLS never enabled would be directly readable/writable by
-- anyone holding the anon key once the app moves to per-user JWT DB access.

-- 1. Enable RLS on tables that were left unprotected.
ALTER TABLE IF EXISTS public.org_invites ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.usage_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.credit_balances ENABLE ROW LEVEL SECURITY;

-- Members can read their own org's usage/credits; nobody can write them from
-- the client (only the service role, which bypasses RLS, mutates billing data).
DROP POLICY IF EXISTS "members read own org usage" ON public.usage_metrics;
CREATE POLICY "members read own org usage" ON public.usage_metrics
  FOR SELECT USING (org_id = public.get_user_org_id());

DROP POLICY IF EXISTS "members read own org credits" ON public.credit_balances;
CREATE POLICY "members read own org credits" ON public.credit_balances
  FOR SELECT USING (org_id = public.get_user_org_id());

DROP POLICY IF EXISTS "members read own org invites" ON public.org_invites;
CREATE POLICY "members read own org invites" ON public.org_invites
  FOR SELECT USING (org_id = public.get_user_org_id());

-- 2. Reconcile the feature-table RLS policies onto the real org model.
-- Migrations 0006-0017 wrote policies against a non-existent
-- projects.owner_user_ids column; the canonical model is projects.org_id +
-- get_user_org_id(). Rewrite them so RLS actually matches (and would enforce
-- correctly if the anon key ever queries these tables directly).
DO $$
DECLARE
  t text;
  pol record;
  feature_tables text[] := ARRAY[
    'bulk_content_jobs','bulk_content_articles','content_calendar','publishing_logs',
    'competitors','competitor_analysis','outrank_strategies',
    'site_pages','internal_link_opportunities','internal_links','link_audit',
    'keywords','keyword_clusters','keyword_mappings','url_assignments','keyword_gaps',
    'languages','localized_content','hreflang_config','region_targeting','translation_jobs',
    'audit_schedules','audit_runs','audit_issues','issue_resolutions','audit_performance_metrics',
    'wins_reports','edge_sites','edge_rules','git_connections','git_pull_requests',
    'product_feeds','feed_products'
  ];
BEGIN
  FOREACH t IN ARRAY feature_tables LOOP
    IF to_regclass('public.' || t) IS NULL THEN
      CONTINUE;
    END IF;
    -- drop every existing policy on the table (they reference owner_user_ids)
    FOR pol IN SELECT policyname FROM pg_policies
               WHERE schemaname = 'public' AND tablename = t LOOP
      EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', pol.policyname, t);
    END LOOP;
    -- ensure RLS is on
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
    -- one org-scoped policy covering all commands, keyed on the project's org
    EXECUTE format($f$
      CREATE POLICY "org members access %1$s" ON public.%1$I
        FOR ALL USING (
          project_id IN (
            SELECT id FROM public.projects WHERE org_id = public.get_user_org_id()
          )
        )
    $f$, t);
  END LOOP;
END $$;

-- git_connections holds access tokens: keep client SELECT blocked entirely.
-- The FOR ALL policy above would allow members to read tokens, so replace it
-- with write-only-by-nobody (service role bypasses RLS for the backend).
DROP POLICY IF EXISTS "org members access git_connections" ON public.git_connections;
-- (no client policy => deny-by-default; only the service role can touch it)
