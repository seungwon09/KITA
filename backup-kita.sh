#!/usr/bin/env bash
set -euo pipefail

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${BACKUP_DIR:-$PWD/backups/$STAMP}"
mkdir -p "$BACKUP_DIR"

docker exec kita-mongo mongodump --db kita --archive --gzip > "$BACKUP_DIR/mongo-kita.archive.gz"
docker run --rm -v kita-deploy_kita_web_data:/source:ro -v "$BACKUP_DIR:/backup" alpine \
  sh -c "cd /source && tar -czf /backup/web-data.tar.gz ."
docker run --rm -v kita-deploy_kita_ai_db:/source:ro -v "$BACKUP_DIR:/backup" alpine \
  sh -c "cd /source && tar -czf /backup/study-ai-data.tar.gz ."

echo "Backup completed: $BACKUP_DIR"
