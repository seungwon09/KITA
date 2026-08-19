@echo off
cd /d "%~dp0"
schtasks /Create /TN "KITA Public Backend Keepalive" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File \"%~dp0KITA_PUBLIC_KEEPALIVE.ps1\"" /SC ONLOGON /RL LIMITED /F
schtasks /Create /TN "KITA Daily Local Backup" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File \"%~dp0BACKUP_KITA_LOCAL.ps1\"" /SC DAILY /ST 03:00 /RL LIMITED /F
echo KITA startup tasks installed.
pause

