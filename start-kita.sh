#!/usr/bin/env bash
set -e

echo "KITA deploy server starting..."

if [ ! -f .env ]; then
  cp .env.example .env
  echo ".env was created. Edit JWT_SECRET, ADMIN_PIN, and PUBLIC_BASE_URL before real release."
  exit 1
fi

docker compose up -d --build

echo "KITA is running."
echo "Web: http://SERVER_IP:3000"
echo "AI:  http://SERVER_IP:8002/docs"
