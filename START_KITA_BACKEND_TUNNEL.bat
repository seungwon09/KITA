@echo off
cd /d "%~dp0"
npx --yes cloudflared tunnel --url http://127.0.0.1:8080 > cloudflared-backend.out.log 2> cloudflared-backend.err.log

