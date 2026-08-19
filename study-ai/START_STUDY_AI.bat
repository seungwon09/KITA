@echo off
title Study AI Server
cd /d C:\Users\user\Documents\Codex\2026-05-20\transformer-pretraining-fine-tuning-rlhf-hallucination
echo Study AI server starting...
echo.
echo Open this address after the server starts:
echo http://127.0.0.1:8001/
echo.
C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts\run_real_server_8001.py
echo.
echo Server stopped. Press any key to close.
pause > nul
