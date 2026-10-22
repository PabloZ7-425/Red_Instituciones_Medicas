#!/bin/bash
set -euo pipefail
umask 077
phase="${1:-inventory}"
case "$PGDATABASE" in hospital|test_b3_*) ;; *) echo 'Destino hospitalario no autorizado' >&2; exit 1;; esac
case "$phase" in inventory|expand|finalize|all|roles) ;; *) echo 'Fase invalida' >&2; exit 1;; esac
psql --set=ON_ERROR_STOP=1 --file=/schema/inventory.sql
if [ "$phase" = inventory ]; then exit 0; fi
backup_dir="${HOSPITAL_BACKUP_ROOT:-/backups}/$(date -u +%Y%m%dT%H%M%SZ)-${phase}-$$"
mkdir "$backup_dir"
pg_dump --format=custom --file="$backup_dir/hospital.dump"
pg_restore --list "$backup_dir/hospital.dump" > "$backup_dir/contenido.txt"
echo "Respaldo verificado: $backup_dir/hospital.dump"
if [ "$phase" = expand ] || [ "$phase" = all ]; then
  psql --set=ON_ERROR_STOP=1 --single-transaction --file=/schema/migrations/001_expand.sql
fi
if [ "$phase" = finalize ] || [ "$phase" = all ]; then
  psql --set=ON_ERROR_STOP=1 --single-transaction --file=/schema/migrations/002_finalize.sql
fi
if [ "$phase" = roles ] || [ "$phase" = all ]; then
  : "${HOSPITAL_APP_PASSWORD:?Configure HOSPITAL_APP_PASSWORD}"
  psql --set=ON_ERROR_STOP=1 --single-transaction --set=app_password="$HOSPITAL_APP_PASSWORD" --file=/schema/runtime_role.sql
fi
