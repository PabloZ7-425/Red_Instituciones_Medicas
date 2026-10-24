#!/bin/sh
set -eu
mkdir -p /data/export
if [ -f /data/export/firebase-export-metadata.json ]; then
    exec firebase emulators:start --only firestore --project demo-historiales \
      --import=/data/export --export-on-exit=/data/export
fi
exec firebase emulators:start --only firestore --project demo-historiales \
  --export-on-exit=/data/export
