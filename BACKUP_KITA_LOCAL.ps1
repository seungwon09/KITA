$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = Join-Path $root "backups\local-$stamp"
$dbDir = Join-Path $backupDir "mongo-json"
New-Item -ItemType Directory -Force -Path $backupDir, $dbDir | Out-Null

Push-Location (Join-Path $root "study-platform")
try {
    node scripts\backup-local-db.js $dbDir
} finally {
    Pop-Location
}

$items = @(
    @{ Path = Join-Path $root "study-platform\data"; Name = "web-data" },
    @{ Path = Join-Path $root "study-platform\uploads"; Name = "uploads" },
    @{ Path = Join-Path $root "study-ai\study_ai.sqlite3"; Name = "study-ai.sqlite3" },
    @{ Path = Join-Path $root ".env.example"; Name = "env-example.txt" },
    @{ Path = Join-Path $root ".env.production.example"; Name = "env-production-example.txt" }
)

foreach ($item in $items) {
    if (Test-Path -LiteralPath $item.Path) {
        $target = Join-Path $backupDir $item.Name
        Copy-Item -LiteralPath $item.Path -Destination $target -Recurse -Force
    }
}

$zip = "$backupDir.zip"
Compress-Archive -Path (Join-Path $backupDir "*") -DestinationPath $zip -Force
Write-Output "KITA local backup completed: $zip"

