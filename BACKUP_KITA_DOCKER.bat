@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0BACKUP_KITA_DOCKER.ps1"
pause
