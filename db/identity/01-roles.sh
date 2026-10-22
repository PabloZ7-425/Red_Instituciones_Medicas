#!/bin/sh
set -eu

# This bootstrap runs ONLY on a new technical volume. Existing volumes are preserved.
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=ON_ERROR_STOP=1 \
  --set=app_password="$IDENTITY_APP_PASSWORD" \
  --set=migrator_password="$IDENTITY_MIGRATOR_PASSWORD" <<'SQL'
CREATE ROLE identidad_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'migrator_password';
CREATE ROLE identidad_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'app_password';
ALTER DATABASE identidad OWNER TO identidad_migrator;
REVOKE ALL ON DATABASE identidad FROM PUBLIC;
GRANT CONNECT ON DATABASE identidad TO identidad_app;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO identidad_migrator;
GRANT USAGE ON SCHEMA public TO identidad_app;
ALTER DEFAULT PRIVILEGES FOR ROLE identidad_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO identidad_app;
ALTER DEFAULT PRIVILEGES FOR ROLE identidad_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO identidad_app;
SQL
