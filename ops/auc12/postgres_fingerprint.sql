-- Aggregate hashes only: never emit patient rows, credentials or session values.
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout='60s';
SELECT format(
  'SELECT %L,COUNT(*),md5(COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text COLLATE "C")::text,%L)) FROM %I.%I AS t;',
  'table:'||schemaname||'.'||tablename,'[]',schemaname,tablename)
FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema')
  AND schemaname NOT LIKE 'pg_toast%' ORDER BY schemaname,tablename
\gexec
SELECT format('SELECT %L,last_value,is_called FROM %I.%I;',
              'sequence:'||schemaname||'.'||sequencename,schemaname,sequencename)
FROM pg_sequences WHERE schemaname NOT IN ('pg_catalog','information_schema')
ORDER BY schemaname,sequencename
\gexec
COMMIT;
