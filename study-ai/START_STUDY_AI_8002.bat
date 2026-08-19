@echo off
cd /d "%~dp0"
echo Study AI server starting on port 8002...
echo.
echo Open this address after the server starts:
echo http://127.0.0.1:8002/
echo.
"C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\run_real_server_8002.py
echo.
echo Server stopped. Press any key to close.
pause > nul
