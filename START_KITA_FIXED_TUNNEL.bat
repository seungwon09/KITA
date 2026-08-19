@echo off
cd /d "%~dp0"

echo Starting KITA Docker server...
docker compose up -d
if errorlevel 1 (
  echo Docker start failed.
  pause
  exit /b 1
)

echo.
echo Starting fixed Cloudflare Tunnel...
echo Keep this window open while KITA is public.
echo.
npx --yes cloudflared tunnel --config "%USERPROFILE%\.cloudflared\kita-prod.yml" run kita-prod
pause
