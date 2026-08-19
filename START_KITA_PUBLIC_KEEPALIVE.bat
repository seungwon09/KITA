@echo off
cd /d "%~dp0"
start "KITA PUBLIC KEEPALIVE" /min powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0KITA_PUBLIC_KEEPALIVE.ps1"

