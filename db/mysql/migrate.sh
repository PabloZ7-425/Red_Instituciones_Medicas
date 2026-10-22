#!/bin/bash
set -euo pipefail
umask 077
phase="${1:-inventory}"
case "$MYSQL_DATABASE" in pediatrico) ;; *) echo 'Destino activo no autorizado' >&2; exit 1;; esac
case "$phase" in inventory|expand|reconcile|finalize|all|roles) ;; *) echo 'Fase invalida' >&2; exit 1;; esac
export MYSQL_PWD="${MYSQL_ROOT_PASSWORD:?Configure MYSQL_ROOT_PASSWORD}"
client=(mysql --host=mysql --user=root --default-character-set=utf8mb4 --batch)
"${client[@]}" "$MYSQL_DATABASE" < /schema/inventory.sql
if [ "$phase" = inventory ]; then exit 0; fi
backup_dir="/backups/$(date -u +%Y%m%dT%H%M%SZ)-${phase}-$$"
mkdir "$backup_dir"
mysqldump --host=mysql --user=root --single-transaction --routines --triggers --events \
  --hex-blob --no-tablespaces --set-gtid-purged=OFF "$MYSQL_DATABASE" > "$backup_dir/pediatria.sql"
test -s "$backup_dir/pediatria.sql"
sha256sum "$backup_dir/pediatria.sql" > "$backup_dir/sha256.txt"
# Every mutation first restores its backup into an isolated, generated database.
# Exact prefix + generated identifier only; never restore over the source volume.
restore_suffix=$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')
restore_db="test_b4_restore_$(date -u +%Y%m%d%H%M%S)_$restore_suffix"
[[ "$restore_db" =~ ^test_b4_restore_[0-9]+_[a-f0-9]{16}$ ]]
restore_created=0
cleanup() {
  if [ "$restore_created" = 1 ]; then
    "${client[@]}" --execute="DROP DATABASE \`$restore_db\`"
    restore_created=0
  fi
}
trap cleanup EXIT
"${client[@]}" --execute="CREATE DATABASE \`$restore_db\` CHARACTER SET utf8mb4"
restore_created=1
"${client[@]}" "$restore_db" < "$backup_dir/pediatria.sql"
# Exact table checksums include legacy tables, not only the new clinical chain.
tables=$("${client[@]}" --skip-column-names --execute="SELECT table_name FROM information_schema.tables WHERE table_schema='$MYSQL_DATABASE' AND table_type='BASE TABLE' ORDER BY table_name")
for table in $tables; do
  [[ "$table" =~ ^[a-zA-Z0-9_]+$ ]]
  "${client[@]}" --skip-column-names "$MYSQL_DATABASE" --execute="CHECKSUM TABLE \`$table\`" | cut -f2 >> "$backup_dir/origen.txt"
  "${client[@]}" --skip-column-names "$restore_db" --execute="CHECKSUM TABLE \`$table\`" | cut -f2 >> "$backup_dir/restore.txt"
done
source_hash=$(sha256sum "$backup_dir/origen.txt" | cut -d' ' -f1)
restore_hash=$(sha256sum "$backup_dir/restore.txt" | cut -d' ' -f1)
test "$source_hash" = "$restore_hash"
cleanup
trap - EXIT
echo "Respaldo y restauracion aislada verificados: $backup_dir/pediatria.sql"
if [ "$phase" = expand ] || [ "$phase" = all ]; then
  "${client[@]}" "$MYSQL_DATABASE" < /schema/migrations/001_expand.sql
fi
if [ "$phase" = reconcile ] || [ "$phase" = all ]; then
  "${client[@]}" "$MYSQL_DATABASE" < /schema/migrations/002_reconcile.sql
fi
if [ "$phase" = finalize ] || [ "$phase" = all ]; then
  "${client[@]}" "$MYSQL_DATABASE" < /schema/migrations/003_finalize.sql
fi
if [ "$phase" = roles ] || [ "$phase" = all ]; then
  : "${PEDIATRIA_APP_PASSWORD:?Configure PEDIATRIA_APP_PASSWORD}"
  password_hex=$(printf '%s' "$PEDIATRIA_APP_PASSWORD" | od -An -v -tx1 | tr -d ' \n')
  { printf "SET @app_password_hex='%s';\n" "$password_hex"; cat /schema/runtime_role.sql; } | "${client[@]}" "$MYSQL_DATABASE"
fi
