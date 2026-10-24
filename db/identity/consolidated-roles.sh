#!/bin/sh
set -eu
: "${IDENTITY_APP_PASSWORD:?Required}"
: "${IDENTITY_MIGRATOR_PASSWORD:?Required}"
# Explicit maintenance only. No clinical table, data or owner password changes.
psql -X --set=ON_ERROR_STOP=1 --set=app_password="$IDENTITY_APP_PASSWORD" \
  --set=migrator_password="$IDENTITY_MIGRATOR_PASSWORD" <<'SQL'
BEGIN;
DO $$ BEGIN
  IF EXISTS (SELECT FROM pg_roles WHERE rolname IN ('identidad_app','identidad_migrator')
             AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication)) THEN
    RAISE EXCEPTION 'Identity roles have unexpected privileges; review required';
  END IF;
END $$;
SELECT 'CREATE ROLE identidad_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION'
 WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname='identidad_migrator') \gexec
SELECT 'CREATE ROLE identidad_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION'
 WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname='identidad_app') \gexec
ALTER ROLE identidad_migrator PASSWORD :'migrator_password';
ALTER ROLE identidad_app PASSWORD :'app_password';
SELECT format('GRANT CONNECT ON DATABASE %I TO identidad_app, identidad_migrator', current_database()) \gexec
CREATE SCHEMA IF NOT EXISTS identidad AUTHORIZATION identidad_migrator;
DO $$ BEGIN
 IF (SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname='identidad') <> 'identidad_migrator' THEN
   RAISE EXCEPTION 'Unexpected identity schema owner';
 END IF;
END $$;
REVOKE ALL ON SCHEMA identidad FROM PUBLIC;
GRANT USAGE ON SCHEMA identidad TO identidad_app;
ALTER DEFAULT PRIVILEGES FOR ROLE identidad_migrator IN SCHEMA identidad
 GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO identidad_app;
ALTER DEFAULT PRIVILEGES FOR ROLE identidad_migrator IN SCHEMA identidad
 GRANT USAGE, SELECT ON SEQUENCES TO identidad_app;
COMMIT;
SQL
