$ErrorActionPreference = "Continue"

$root = $PSScriptRoot
$firebaseCli = Join-Path $env:APPDATA "npm\node_modules\firebase-tools\lib\bin\firebase.js"
$frontendConfig = Join-Path $root "study-platform\public\kita-runtime-config.js"
$tunnelErr = Join-Path $root "cloudflared-backend.err.log"
$tunnelOut = Join-Path $root "cloudflared-backend.out.log"
$publicLinkFile = Join-Path ([Environment]::GetFolderPath("Desktop")) "KITA 공개링크.txt"
$webUrl = "https://kita-ec927.web.app"

function Test-HttpOk($url) {
    try {
        $res = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 8
        return $res.StatusCode -ge 200 -and $res.StatusCode -lt 500
    } catch {
        return $false
    }
}

function Start-StudyAi {
    if (Test-HttpOk "http://127.0.0.1:8002/health") { return }
    Start-Process -WindowStyle Hidden -WorkingDirectory (Join-Path $root "study-ai") -FilePath "powershell.exe" -ArgumentList "-NoProfile","-Command","`$env:PYTHONIOENCODING='utf-8'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8002 *> server8002.out.log"
    Start-Sleep -Seconds 5
}

function Start-WebApi {
    if (Test-HttpOk "http://127.0.0.1:8080/api/health") { return }
    Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Start-Process -WindowStyle Hidden -WorkingDirectory (Join-Path $root "study-platform") -FilePath "node.exe" -ArgumentList "src/server.js"
    Start-Sleep -Seconds 6
}

function Start-Tunnel {
    $current = Get-TunnelUrl
    if ($current -and (Test-HttpOk "$current/api/health")) { return $current }
    Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $tunnelErr, $tunnelOut -Force -ErrorAction SilentlyContinue
    Start-Process -WindowStyle Hidden -WorkingDirectory $root -FilePath "cmd.exe" -ArgumentList "/c","npx --yes cloudflared tunnel --url http://127.0.0.1:8080 > cloudflared-backend.out.log 2> cloudflared-backend.err.log"
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 2
        $url = Get-TunnelUrl
        if ($url -and (Test-HttpOk "$url/api/health")) { return $url }
    }
    return ""
}

function Get-TunnelUrl {
    if (!(Test-Path -LiteralPath $tunnelErr)) { return "" }
    $match = Select-String -Path $tunnelErr -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" | Select-Object -Last 1
    if (!$match) { return "" }
    return $match.Matches[0].Value
}

function Update-FirebaseFrontend($apiUrl) {
    if (!$apiUrl) { return }
    $content = "window.KITA_API_BASE = `"$apiUrl`";"
    $old = if (Test-Path -LiteralPath $frontendConfig) { Get-Content -LiteralPath $frontendConfig -Raw } else { "" }
    if ($old.Trim() -eq $content) { return }
    Set-Content -LiteralPath $frontendConfig -Value $content -Encoding UTF8
    if (Test-Path -LiteralPath $firebaseCli) {
        Push-Location $root
        try {
            node $firebaseCli deploy --only hosting --project kita-ec927
        } finally {
            Pop-Location
        }
    }
}

function Write-LinkFile($apiUrl) {
    $text = @"
KITA 공개링크
$webUrl

KITA 공개 백엔드 API
$apiUrl

주의: 현재 백엔드는 이 노트북이 켜져 있고 KITA_PUBLIC_KEEPALIVE가 실행 중일 때 작동합니다.
"@
    Set-Content -LiteralPath $publicLinkFile -Value $text -Encoding UTF8
}

Start-Transcript -Path (Join-Path $root "kita-keepalive.log") -Append | Out-Null
while ($true) {
    Start-StudyAi
    Start-WebApi
    $apiUrl = Start-Tunnel
    if ($apiUrl) {
        Update-FirebaseFrontend $apiUrl
        Write-LinkFile $apiUrl
    }
    Start-Sleep -Seconds 60
}

