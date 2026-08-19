@echo off
cd /d "%~dp0"
echo Stopping KITA Docker server...
docker compose down
pause
