# KITA restore

1. Stop writes before restoring: `docker compose --env-file .env.production -f docker-compose.prod.yml stop kita-web kita-ai`
2. Restore MongoDB: `cat backups/DATE/mongo-kita.archive.gz | docker exec -i kita-mongo mongorestore --drop --archive --gzip`
3. Restore the `web-data.tar.gz` and `study-ai-data.tar.gz` archives into their matching Docker volumes.
4. Start services: `docker compose --env-file .env.production -f docker-compose.prod.yml up -d`
