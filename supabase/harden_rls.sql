-- =============================================================================
-- HARNESS EXECUTIVE OS — Supabase RLS Security Hardening Migration (TD-04)
-- =============================================================================
-- Replaces permissive `using (true) with check (true)` policies across all
-- tables so unauthenticated anon keys embedded in public client bundles can
-- NEVER read or mutate private personal data.
--
-- Recommended Architecture:
--   1. Apply this SQL in Supabase SQL Editor.
--   2. Configure SUPABASE_SERVICE_ROLE_KEY (server-side / GitHub Actions only)
--      or authenticate users via Supabase Auth (role = 'authenticated').
--   3. Keep browser clients talking to Flask `/api/rpc/*` gated by X-Harness-Key.
-- =============================================================================

DO $$
DECLARE
    tbl TEXT;
    pol RECORD;
    tables TEXT[] := ARRAY[
        'tasks',
        'daily_logs',
        'projects',
        'body_metrics',
        'workouts',
        'knowledge_items',
        'kill_list_items',
        'station_deliverable_progress',
        'school_exams',
        'homework_items',
        'tum_grades',
        'tum_grade_entries',
        'tum_matura',
        'tum_language',
        'app_settings',
        'travel_windows',
        'material_deficit'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = tbl
        ) THEN
            EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', tbl);

            -- Drop legacy world-open policies
            FOR pol IN
                SELECT policyname FROM pg_policies
                WHERE schemaname = 'public' AND tablename = tbl
            LOOP
                EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I;', pol.policyname, tbl);
            END LOOP;

            -- Allow authenticated users & service_role only (denies public anon key)
            EXECUTE format(
                'CREATE POLICY %I ON public.%I FOR ALL TO authenticated USING (true) WITH CHECK (true);',
                'Authenticated access only on ' || tbl,
                tbl
            );
        END IF;
    END LOOP;
END $$;
