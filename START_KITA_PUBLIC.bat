@echo off
cd /d "%~dp0"
echo Starting KITA Docker server...
docker compose up -d --build
echo.
echo KITA local:
echo http://127.0.0.1:3000
echo.
echo Creating public temporary link...
echo Keep this window open while friends use KITA.
echo Copy the trycloudflare.com link that appears below.
echo.
npx --yes cloudflared tunnel --url http://localhost:3000
pause
