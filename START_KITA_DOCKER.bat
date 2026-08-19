@echo off
cd /d "%~dp0"
echo Starting KITA Docker server...
docker compose up -d --build
echo.
echo KITA is running:
echo http://127.0.0.1:3000
echo.
echo Same Wi-Fi phone link:
echo http://172.30.1.37:3000
pause
