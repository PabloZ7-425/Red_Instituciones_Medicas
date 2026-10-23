#!/bin/bash
set -euo pipefail
umask 077
# Stop all writers before invoking. Source is fixed; no arbitrary remote URI.
export MONGO_VERIFY_URI='mongodb://mongo:27017/?directConnection=true'
suffix=$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')
prefix=""
case "${1:-backup}" in
  backup)
    backup_dir="/backups/$(date -u +%Y%m%dT%H%M%SZ)-$suffix"
    mkdir "$backup_dir"
    ;;
  verify)
    [[ "${2:-}" =~ ^[0-9]{8}T[0-9]{6}Z-[a-f0-9]{16}$ ]]
    backup_dir="/backups/$2"
    sha256sum --check "$backup_dir/sha256.txt"
    prefix="verificacion_"
    ;;
  *) echo 'Use backup o verify <directorio_respaldo>' >&2; exit 1;;
esac
mongosh --quiet --nodb /ops/manifest.js > "$backup_dir/${prefix}origen.json"
if [ "$prefix" = "" ]; then
  mongodump --uri="$MONGO_VERIFY_URI" --archive="$backup_dir/mongo.archive.gz" --gzip
  sha256sum "$backup_dir/mongo.archive.gz" > "$backup_dir/sha256.txt"
fi
# Restore into a separate mongod inside this disposable maintenance container.
# It has no access to /data/db of the active service.
probe_dir=$(mktemp -d /tmp/b5-mongo-XXXXXXXX)
mkdir "$probe_dir/db"
cleanup() { mongod --shutdown --dbpath "$probe_dir/db" > /dev/null; }
mongod --dbpath "$probe_dir/db" --bind_ip 127.0.0.1 --port 27028 --fork --logpath "$probe_dir/mongod.log"
trap cleanup EXIT
mongorestore --uri='mongodb://127.0.0.1:27028/?directConnection=true' --archive="$backup_dir/mongo.archive.gz" --gzip --stopOnError
MONGO_VERIFY_URI='mongodb://127.0.0.1:27028/?directConnection=true' mongosh --quiet --nodb /ops/manifest.js > "$backup_dir/${prefix}restore.json"
mongosh --quiet --nodb /ops/manifest.js > "$backup_dir/${prefix}origen_despues.json"
original=$(sha256sum "$backup_dir/${prefix}origen.json" | cut -d' ' -f1)
restored=$(sha256sum "$backup_dir/${prefix}restore.json" | cut -d' ' -f1)
after=$(sha256sum "$backup_dir/${prefix}origen_despues.json" | cut -d' ' -f1)
test "$original" = "$restored"
test "$original" = "$after"
echo "Respaldo restaurado y hashes/cantidades/indices/validadores conservados: $backup_dir"
