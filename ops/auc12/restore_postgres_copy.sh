#!/bin/sh
# Restore a host-supplied archive only into a generated verification database.
set -eu
umask 077
case "${AUC12_SOURCE_DB:?}:${AUC12_COPY_DB:?}" in
  hospital:test_b3_auc12_*|identidad:test_auc12_identity_*) ;;
  *) echo 'Destino de verificacion invalido' >&2; exit 1 ;;
esac
case "$AUC12_COPY_DB" in *[!a-z0-9_]*) exit 1 ;; esac
case "${AUC12_WORK:?}" in /tmp/auc12_verify_*) ;; *) exit 1 ;; esac
case "$AUC12_WORK" in *..*) exit 1 ;; esac
archive="$AUC12_WORK/backup.dump"
actual=$(sha256sum "$archive");actual=${actual%% *}
[ "$actual" = "${AUC12_ARCHIVE_SHA:?}" ] || { echo 'Hash del respaldo no coincide' >&2;exit 1; }
# createdb fails on an existing name. Never drop/clean/overwrite any database.
createdb --host=/var/run/postgresql --username="$POSTGRES_USER" "$AUC12_COPY_DB"
psql -X -q --host=/var/run/postgresql --username="$POSTGRES_USER" --dbname="$AUC12_COPY_DB" \
  --set=ON_ERROR_STOP=1 --command="REVOKE ALL ON DATABASE $AUC12_COPY_DB FROM PUBLIC"
pg_restore --host=/var/run/postgresql --username="$POSTGRES_USER" --dbname="$AUC12_COPY_DB" \
  --exit-on-error --no-owner --no-privileges "$archive"
export PGTZ=UTC
psql -X -qAt --host=/var/run/postgresql --username="$POSTGRES_USER" --dbname="$AUC12_SOURCE_DB" \
  --set=ON_ERROR_STOP=1 --file="$AUC12_WORK/postgres_fingerprint.sql" > "$AUC12_WORK/source.txt"
psql -X -qAt --host=/var/run/postgresql --username="$POSTGRES_USER" --dbname="$AUC12_COPY_DB" \
  --set=ON_ERROR_STOP=1 --file="$AUC12_WORK/postgres_fingerprint.sql" > "$AUC12_WORK/copy.txt"
source_hash=$(sha256sum "$AUC12_WORK/source.txt");source_hash=${source_hash%% *}
copy_hash=$(sha256sum "$AUC12_WORK/copy.txt");copy_hash=${copy_hash%% *}
[ "$source_hash" = "$copy_hash" ] || { echo 'La copia no coincide con el origen actual; no se modifico el origen' >&2;exit 1; }
printf '%s\n' "$copy_hash"
