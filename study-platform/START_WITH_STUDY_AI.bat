@echo off
setlocal
set STUDY_AI_DIR=C:\Users\user\Documents\Codex\2026-05-20\transformer-pretraining-fine-tuning-rlhf-hallucination
set STUDY_PLATFORM_DIR=C:\Users\user\Desktop\study-platform

echo KITA starting...

netstat -ano | findstr /R /C:"127.0.0.1:8002 .*LISTENING" >nul
if errorlevel 1 (
    echo Starting Study AI backend on 8002...
    start "Study AI 8002" /D "%STUDY_AI_DIR%" "%STUDY_AI_DIR%\START_STUDY_AI_8002.bat"
) else (
    echo Study AI backend already running on 8002.
)

cd /d "%STUDY_PLATFORM_DIR%"
echo Starting KITA UI on 3000...
echo Open: http://127.0.0.1:3000/
npm.cmd start
pause
