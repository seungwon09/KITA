@echo off
echo Stopping cloudflared tunnel processes...
taskkill /IM cloudflared.exe /F 2>nul
echo Done.
pause
