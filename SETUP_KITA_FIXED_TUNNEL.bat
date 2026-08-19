@echo off
setlocal
cd /d "%~dp0"

echo.
echo [KITA] Fixed Cloudflare Tunnel setup
echo.
echo This creates a stable public URL such as:
echo   https://kita.your-domain.com
echo.
echo Requirements:
echo   1. Cloudflare account
echo   2. A domain added to Cloudflare
echo   3. Docker Desktop running
echo.

set /p KITA_HOSTNAME=Enter fixed hostname, for example kita.example.com: 
if "%KITA_HOSTNAME%"=="" (
  echo Hostname is required.
  pause
  exit /b 1
)

echo.
echo Step 1/5: Starting local KITA...
docker compose up -d --build
if errorlevel 1 (
  echo Docker start failed.
  pause
  exit /b 1
)

echo.
echo Step 2/5: Logging in to Cloudflare.
echo A browser window will open. Pick the Cloudflare domain you want to use.
npx --yes cloudflared tunnel login
if errorlevel 1 (
  echo Cloudflare login failed.
  pause
  exit /b 1
)

echo.
echo Step 3/5: Creating tunnel named kita-prod if needed...
npx --yes cloudflared tunnel create kita-prod
echo.
echo Existing tunnels:
npx --yes cloudflared tunnel list
echo.
set /p TUNNEL_ID=Paste the kita-prod Tunnel ID shown above: 
if "%TUNNEL_ID%"=="" (
  echo Tunnel ID is required.
  pause
  exit /b 1
)

echo.
echo Step 4/5: Creating DNS route...
npx --yes cloudflared tunnel route dns kita-prod %KITA_HOSTNAME%
if errorlevel 1 (
  echo DNS route failed. Check that the domain is on the same Cloudflare account.
  pause
  exit /b 1
)

echo.
echo Step 5/5: Writing local tunnel config...
if not exist "%USERPROFILE%\.cloudflared" mkdir "%USERPROFILE%\.cloudflared"
(
  echo tunnel: %TUNNEL_ID%
  echo credentials-file: %USERPROFILE%\.cloudflared\%TUNNEL_ID%.json
  echo ingress:
  echo   - hostname: %KITA_HOSTNAME%
  echo     service: http://localhost:3000
  echo   - service: http_status:404
) > "%USERPROFILE%\.cloudflared\kita-prod.yml"

(
  echo KITA_HOSTNAME=%KITA_HOSTNAME%
  echo TUNNEL_ID=%TUNNEL_ID%
  echo CONFIG=%USERPROFILE%\.cloudflared\kita-prod.yml
  echo URL=https://%KITA_HOSTNAME%
) > "%~dp0KITA_FIXED_LINK.txt"

echo.
echo Done.
echo Fixed KITA URL:
echo https://%KITA_HOSTNAME%
echo.
echo To run it later, use:
echo START_KITA_FIXED_TUNNEL.bat
pause
