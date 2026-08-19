$ErrorActionPreference = 'Stop'

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupRoot = Join-Path $PSScriptRoot 'backups'
$backupDir = Join-Path $backupRoot $stamp
$mongoTemp = "/tmp/kita-backup-$stamp"

New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

docker exec kita-mongo mongodump --db kita --out $mongoTemp
if ($LASTEXITCODE -ne 0) { throw 'MongoDB backup failed.' }
docker cp "kita-mongo:${mongoTemp}" (Join-Path $backupDir 'mongo')
if ($LASTEXITCODE -ne 0) { throw 'MongoDB backup copy failed.' }
docker exec kita-mongo rm -rf $mongoTemp

docker run --rm -v kita-deploy_kita_web_data:/source:ro -v "${backupDir}:/backup" alpine sh -c "cd /source && tar -czf /backup/web-data.tar.gz ."
if ($LASTEXITCODE -ne 0) { throw 'Web data backup failed.' }
docker run --rm -v kita-deploy_kita_ai_db:/source:ro -v "${backupDir}:/backup" alpine sh -c "cd /source && tar -czf /backup/study-ai-data.tar.gz ."
if ($LASTEXITCODE -ne 0) { throw 'Study AI backup failed.' }

Write-Output "KITA backup completed: $backupDir"
