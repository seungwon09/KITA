#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env.production ]; then
  cp .env.production.example .env.production
  echo ".env.production was created. Set KITA_DOMAIN, JWT_SECRET, ADMIN_PIN, and MONGO_PASSWORD, then run this script again."
  exit 1
fi

set -a
source .env.production
set +a

if [ "${#JWT_SECRET}" -lt 48 ]; then
  echo "JWT_SECRET must be at least 48 characters."
  exit 1
fi
if [ "${#ADMIN_PIN}" -lt 10 ]; then
  echo "ADMIN_PIN must be at least 10 characters."
  exit 1
fi
if [ "${#MONGO_PASSWORD}" -lt 20 ]; then
  echo "MONGO_PASSWORD must be at least 20 characters."
  exit 1
fi
if [ "$PUBLIC_BASE_URL" != "https://$KITA_DOMAIN" ]; then
  echo "PUBLIC_BASE_URL must exactly match https://KITA_DOMAIN."
  exit 1
fi

docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
docker exec kita-ollama ollama pull "${LOCAL_LLM_MODEL:-qwen2.5:3b}"
docker compose --env-file .env.production -f docker-compose.prod.yml restart kita-web kita-ai

echo "KITA production stack is running."
