-- Least-privilege application role for Frontdesk — the prerequisite for
-- Row-Level Security to actually enforce (RLS is ignored for superusers and
-- any role with BYPASSRLS).
--
-- Run as a superuser against each environment's database, then point
-- DATABASE_URL / DATABASE_URL_SYNC at this role to ACTIVATE enforcement:
--
--   psql -U postgres -d frontdesk_db -v app_password="'a-strong-password'" \
--        -f scripts/create_app_role.sql
--
-- The role is NOSUPERUSER + NOBYPASSRLS and is NOT the table owner, so the RLS
-- policies (see the a83dce9a149a migration) apply to it.

\set app_password :app_password

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'frontdesk_app') THEN
    EXECUTE format(
      'CREATE ROLE frontdesk_app LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS',
      :'app_password'
    );
  END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO frontdesk_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO frontdesk_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO frontdesk_app;

-- Tables/sequences created by future migrations inherit the same grants.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO frontdesk_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO frontdesk_app;
