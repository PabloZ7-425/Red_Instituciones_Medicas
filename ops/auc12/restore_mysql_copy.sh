#!/bin/sh
# Restore only into a new generated database. Source is SELECT/CHECKSUM only.
set -eu
umask 077
[ "${MYSQL_DATABASE:?}" = 'pediatrico' ]
case "${AUC12_COPY_DB:?}" in test_b4_auc12_*) ;; *) exit 1 ;; esac
case "$AUC12_COPY_DB" in *[!a-z0-9_]*) exit 1 ;; esac
case "${AUC12_WORK:?}" in /tmp/auc12_verify_*) ;; *) exit 1 ;; esac
case "$AUC12_WORK" in *..*) exit 1 ;; esac
export MYSQL_PWD="${MYSQL_ROOT_PASSWORD:?}"
archive="$AUC12_WORK/backup.sql"
actual=$(sha256sum "$archive");actual=${actual%% *}
[ "$actual" = "${AUC12_ARCHIVE_SHA:?}" ] || { echo 'Hash del respaldo no coincide' >&2;exit 1; }
# mysqldump without --databases must not switch to or drop the source database.
if grep -Eiq '^[[:space:]]*((CREATE|DROP)[[:space:]]+DATABASE|USE[[:space:]])' "$archive";then
  echo 'El dump contiene cambios de base no permitidos; se requiere revisar' >&2;exit 1
fi
metadata=$(mysql --protocol=SOCKET --user=root --batch --skip-column-names --execute="SELECT DEFAULT_CHARACTER_SET_NAME,DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='pediatrico'")
# Server metadata supplies fixed charset/collation identifiers (no free SQL).
set -- $metadata
charset=${1:?};collation=${2:?}
case "$charset:$collation" in *[!a-zA-Z0-9_:]*) exit 1 ;; esac
mysql --protocol=SOCKET --user=root --execute="CREATE DATABASE $AUC12_COPY_DB CHARACTER SET $charset COLLATE $collation"
mysql --protocol=SOCKET --user=root --database="$AUC12_COPY_DB" < "$archive"
source_tables=$(mysql --protocol=SOCKET --user=root --batch --skip-column-names --execute="SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='pediatrico' AND TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME")
copy_tables=$(mysql --protocol=SOCKET --user=root --batch --skip-column-names --execute="SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='$AUC12_COPY_DB' AND TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME")
[ "$source_tables" = "$copy_tables" ] || { echo 'Lista de tablas restauradas incompatible' >&2;exit 1; }
: > "$AUC12_WORK/source.txt"
: > "$AUC12_WORK/copy.txt"
for table in $source_tables;do
  case "$table" in *[!a-zA-Z0-9_]*) echo 'Nombre de tabla no soportado' >&2;exit 1 ;; esac
  for db in pediatrico "$AUC12_COPY_DB";do
    count=$(mysql --protocol=SOCKET --user=root --batch --skip-column-names --database="$db" --execute="SELECT COUNT(*) FROM \`$table\`")
    checksum=$(mysql --protocol=SOCKET --user=root --batch --skip-column-names --database="$db" --execute="CHECKSUM TABLE \`$table\` EXTENDED" | cut -f2)
    case "$checksum" in ''|*[!0-9]*) echo 'No se pudo verificar checksum de tabla' >&2;exit 1 ;; esac
    if [ "$db" = 'pediatrico' ];then target=source;else target=copy;fi
    printf '%s\t%s\t%s\n' "$table" "$count" "$checksum" >> "$AUC12_WORK/$target.txt"
  done
done
source_hash=$(sha256sum "$AUC12_WORK/source.txt");source_hash=${source_hash%% *}
copy_hash=$(sha256sum "$AUC12_WORK/copy.txt");copy_hash=${copy_hash%% *}
[ "$source_hash" = "$copy_hash" ] || { echo 'La copia no coincide con el origen actual; no se modifico el origen' >&2;exit 1; }
printf '%s\n' "$copy_hash"
