$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "study-platform")
$env:NODE_ENV = "development"
$env:PORT = "8080"
$env:MONGO_URI = "mongodb://127.0.0.1:27017/kita"
$env:STUDY_AI_BASE_URL = "http://127.0.0.1:8002"
$env:CORS_ORIGINS = "https://kita-ec927.web.app,https://kita-ec927.firebaseapp.com,http://127.0.0.1:8080,http://localhost:8080"
$env:PUBLIC_BASE_URL = "http://127.0.0.1:8080"
$env:TRUST_PROXY = "false"
$env:STRICT_PRODUCTION_SECURITY = "false"
$env:ENFORCE_HTTPS = "false"
node src/server.js *> (Join-Path $PSScriptRoot "kita-web-8080.out.log")

