# ============================================================================
#  Switch docker-compose.yml from localhost-only to LAN-accessible
#  Run:  powershell -File Update-Docker-Remote.ps1
# ============================================================================
$BASE_DIR = "D:\ERP System\BIO_ERP"
$LAUNCHER = "$BASE_DIR\launcher"
$COMPOSE  = "$BASE_DIR\docker-compose.yml"
$BACKUP   = "$BASE_DIR\docker-compose.yml.bak.local"
$REMOTE   = "$LAUNCHER\docker-compose-remote.yml"
$NGINX    = "$LAUNCHER\nginx-remote.conf"

Write-Host "Switching docker-compose.yml to remote/LAN mode..." -ForegroundColor Cyan

if (-not (Test-Path $COMPOSE)) {
    Write-Host "[WARN] No existing docker-compose.yml - using remote as new file." -ForegroundColor Yellow
    Copy-Item $REMOTE $COMPOSE -Force
} else {
    # Backup the original
    if (-not (Test-Path $BACKUP)) {
        Copy-Item $COMPOSE $BACKUP -Force
        Write-Host "  [OK] Backed up original to $BACKUP" -ForegroundColor Green
    }
    Copy-Item $REMOTE $COMPOSE -Force
    Write-Host "  [OK] Replaced docker-compose.yml with remote version" -ForegroundColor Green
}

# Copy nginx config
if (-not (Test-Path $BASE_DIR\nginx.conf")) {
    Copy-Item $NGINX $BASE_DIR\nginx.conf -Force
    Write-Host "  [OK] Copied nginx.conf to $BASE_DIR" -ForegroundColor Green
}

Write-Host ""
Write-Host "Done! Now start with:" -ForegroundColor Green
Write-Host "  cd $BASE_DIR" -ForegroundColor White
Write-Host "  docker-compose up --build" -ForegroundColor White
Write-Host ""
Write-Host "Access from other devices:" -ForegroundColor Green
Write-Host "  http://<this-pc-ip>:9001" -ForegroundColor White
Write-Host "  http://<this-pc-ip>      (via nginx on port 80)" -ForegroundColor White
