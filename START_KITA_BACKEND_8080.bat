@echo off
cd /d "%~dp0study-platform"
set NODE_ENV=development
set PORT=8080
set MONGO_URI=mongodb://127.0.0.1:27017/kita
set STUDY_AI_BASE_URL=http://127.0.0.1:8002
set CORS_ORIGINS=https://kita-ec927.web.app,https://kita-ec927.firebaseapp.com,http://127.0.0.1:8080,http://localhost:8080
set PUBLIC_BASE_URL=http://127.0.0.1:8080
set TRUST_PROXY=false
set STRICT_PRODUCTION_SECURITY=false
set ENFORCE_HTTPS=false
node src/server.js

