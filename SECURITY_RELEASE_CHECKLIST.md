# KITA release security checklist

Before a public launch:

1. Copy `.env.production.example` to `.env.production`.
2. Replace `JWT_SECRET` with a random value of at least 48 characters.
3. Replace `ADMIN_PIN` with a private value of at least 10 characters.
4. Replace `MONGO_PASSWORD` with a random value of at least 20 characters.
5. Set `KITA_DOMAIN`, `PUBLIC_BASE_URL`, `CORS_ORIGINS`, and `KAKAO_REDIRECT_URI` to the real HTTPS domain.
6. Keep `STRICT_PRODUCTION_SECURITY=true`, `ALLOW_DEV_PAYMENTS=false`, and `ENFORCE_HTTPS=true`.
7. Add Toss live keys only on the server. Never commit `.env.production`.
8. Allow inbound firewall ports `80` and `443` only. Do not expose MongoDB, Ollama, or Study AI ports.
9. Run `./deploy-production.sh`; it refuses weak production secrets.
10. Run `./backup-kita.sh` and confirm the backup archive exists.
