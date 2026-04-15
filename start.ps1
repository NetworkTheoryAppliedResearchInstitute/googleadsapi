# start.ps1 — Auto-start Google Ads API stack on Windows login
# Scheduled via Task Scheduler — runs as current user at logon

$projectDir = "C:\Users\Jodson Graves\Documents\GoogleAdsAPI"
$logFile    = "$projectDir\startup.log"

"[$(Get-Date)] Waiting for Docker Desktop..." | Add-Content $logFile

# Wait up to 3 minutes for Docker Desktop to be ready
$timeout = 180
$elapsed = 0
while ($elapsed -lt $timeout) {
    $result = docker info 2>&1
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 5
    $elapsed += 5
}

if ($LASTEXITCODE -ne 0) {
    "[$(Get-Date)] ERROR: Docker not ready after ${timeout}s. Aborting." | Add-Content $logFile
    exit 1
}

"[$(Get-Date)] Docker ready. Starting Google Ads API stack..." | Add-Content $logFile

Set-Location $projectDir
$output = docker compose up -d 2>&1
$output | Add-Content $logFile

"[$(Get-Date)] Done." | Add-Content $logFile
