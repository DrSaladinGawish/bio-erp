# ============================================================================
#  IncentiveHouse ERP - Push to Docker (full pipeline)
#  Run in PowerShell:  .\Push-ToDocker.ps1
# ============================================================================
$ErrorActionPreference = "Stop"

$BASE = "D:\ERP System\BIO_ERP"
Set-Location $BASE

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  IncentiveHouse ERP - Docker Push Pipeline" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verify Docker is installed
Write-Host "[1/7] Checking Docker installation..." -ForegroundColor Yellow
try {
    $dockerVer = docker --version
    Write-Host "  [OK] $dockerVer" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Docker not found!" -ForegroundColor Red
    Write-Host "  Download Docker Desktop: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    Write-Host "  After install, restart PowerShell and re-run this script." -ForegroundColor Yellow
    pause
    exit 1
}

# 2. Check Docker daemon is running
Write-Host ""
Write-Host "[2/7] Checking Docker daemon..." -ForegroundColor Yellow
try {
    docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERROR] Docker daemon not running. Start Docker Desktop first." -ForegroundColor Red
        pause
        exit 1
    }
    Write-Host "  [OK] Docker daemon is running" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Cannot connect to Docker daemon" -ForegroundColor Red
    pause
    exit 1
}

# 3. Verify Dockerfile, compose, nginx.conf exist
Write-Host ""
Write-Host "[3/7] Verifying deployment files..." -ForegroundColor Yellow
$files = @("Dockerfile", "docker-compose.yml", "nginx.conf", ".dockerignore")
foreach ($f in $files) {
    $p = Join-Path $BASE $f
    if (Test-Path $p) {
        $size = (Get-Item $p).Length
        Write-Host "  [OK] $f ($size bytes)" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] $f" -ForegroundColor Red
    }
}

# 4. Build the image
Write-Host ""
Write-Host "[4/7] Building Docker image (this may take 2-5 minutes)..." -ForegroundColor Yellow
$buildLog = Join-Path $BASE "logs\docker-build.log"
if (-not (Test-Path (Join-Path $BASE "logs"))) { New-Item -ItemType Directory -Path (Join-Path $BASE "logs") -Force | Out-Null }

$buildResult = docker-compose build 2>&1 | Tee-Object -FilePath $buildLog
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [ERROR] Build failed. Last 30 lines of log:" -ForegroundColor Red
    Get-Content $buildLog -Tail 30
    pause
    exit 1
}
Write-Host "  [OK] Build succeeded" -ForegroundColor Green

# 5. List images
Write-Host ""
Write-Host "[5/7] Built images:" -ForegroundColor Yellow
docker images | Select-String "ih-erp" | ForEach-Object { Write-Host "  $_" -ForegroundColor Cyan }

# 6. Start the container
Write-Host ""
Write-Host "[6/7] Starting containers (foreground or detached)..." -ForegroundColor Yellow
$answer = Read-Host "  Start in DETACHED mode (background)? [y/n]"
if ($answer -eq "y" -or $answer -eq "Y") {
    docker-compose up -d
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERROR] docker-compose up failed" -ForegroundColor Red
        pause
        exit 1
    }
    Write-Host "  [OK] Started in background" -ForegroundColor Green
    Start-Sleep -Seconds 5
} else {
    Write-Host "  Starting in foreground. Press CTRL+C to stop." -ForegroundColor Cyan
    docker-compose up
    return
}

# 7. Verify it's running + show access info
Write-Host ""
Write-Host "[7/7] Verifying deployment..." -ForegroundColor Yellow
docker-compose ps

# Wait for healthcheck
Write-Host ""
Write-Host "  Waiting for healthcheck (up to 60s)..." -ForegroundColor Yellow
$healthy = $false
for ($i = 0; $i -lt 12; $i++) {
    Start-Sleep -Seconds 5
    $status = docker inspect --format='{{.State.Health.Status}}' ih-erp-app 2>&1
    if ($status -eq "healthy") {
        $healthy = $true
        Write-Host "  [OK] Container is HEALTHY" -ForegroundColor Green
        break
    }
    Write-Host "    ...still starting ($status)" -ForegroundColor Gray
}

# Show the final result
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  IncentiveHouse ERP - DEPLOYED!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

$pcIp = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.InterfaceAlias -like "*Ethernet*" -or $_.InterfaceAlias -like "*Wi-Fi*"
}).IPAddress | Select-Object -First 1

Write-Host "  Access URLs:" -ForegroundColor Cyan
Write-Host "    On this PC  : http://localhost:9001" -ForegroundColor White
Write-Host "    On this PC  : http://localhost      (via nginx on port 80)" -ForegroundColor White
if ($pcIp) {
    Write-Host "    On LAN     : http://${pcIp}:9001" -ForegroundColor White
    Write-Host "    On LAN     : http://${pcIp}      (via nginx)" -ForegroundColor White
}
Write-Host ""
Write-Host "  Container status:" -ForegroundColor Cyan
docker ps --filter "name=ih-erp" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
Write-Host ""
Write-Host "  Useful commands:" -ForegroundColor Cyan
Write-Host "    View logs   : docker-compose logs -f" -ForegroundColor White
Write-Host "    Stop        : docker-compose down" -ForegroundColor White
Write-Host "    Restart     : docker-compose restart" -ForegroundColor White
Write-Host "    Shell in    : docker exec -it ih-erp-app bash" -ForegroundColor White
Write-Host ""

# Optional: push to Docker Hub
Write-Host "  Push to Docker Hub?" -ForegroundColor Cyan
$push = Read-Host "    Enter Docker Hub username (or press Enter to skip)"
if ($push) {
    $repo = "${push}/incentivehouse-erp:latest"
    Write-Host "  Tagging image as $repo..." -ForegroundColor Yellow
    docker tag ih-erp-app $repo
    Write-Host "  Logging in to Docker Hub..." -ForegroundColor Yellow
    docker login -u $push
    Write-Host "  Pushing $repo..." -ForegroundColor Yellow
    docker push $repo
    Write-Host "  [OK] Pushed! Others can now run:" -ForegroundColor Green
    Write-Host "       docker pull $repo" -ForegroundColor White
    Write-Host "       docker run -d -p 9001:9001 $repo" -ForegroundColor White
}
