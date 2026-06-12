# refresh_env.ps1 — BIO_ERP Development Environment One-Click Refresh
# Generated 2026-06-04 by Machine File Sorting & Efficiency Refresh
# Usage: .\refresh_env.ps1

$ErrorActionPreference = "Continue"
$script:passed = 0
$script:failed = 0
$script:skipped = 0

function Write-Step($msg) {
    Write-Host "`n=== $msg ===" -ForegroundColor Cyan
}

function Write-Pass($msg) {
    Write-Host "  [PASS] $msg" -ForegroundColor Green
    $script:passed++
}

function Write-Fail($msg) {
    Write-Host "  [FAIL] $msg" -ForegroundColor Red
    $script:failed++
}

function Write-Skip($msg) {
    Write-Host "  [SKIP] $msg" -ForegroundColor Yellow
    $script:skipped++
}

# ─────────────────────────────────────────────
# 1. Environment & Paths
# ─────────────────────────────────────────────
Write-Step "1. Setting PYTHONPATH"
$env:PYTHONPATH = "D:\ERP System\BIO_ERP"
Write-Pass "PYTHONPATH = $env:PYTHONPATH"

# ─────────────────────────────────────────────
# 2. Virtual Environment (if exists)
# ─────────────────────────────────────────────
Write-Step "2. Checking virtual environment"
$venvPaths = @(
    "D:\ERP System\BIO_ERP\.venv\Scripts\Activate.ps1",
    "D:\ERP System\BIO_ERP\venv\Scripts\Activate.ps1",
    "$env:USERPROFILE\.virtualenvs\bio_erp\Scripts\Activate.ps1"
)
$foundVenv = $false
foreach ($vp in $venvPaths) {
    if (Test-Path $vp) {
        Write-Pass "Virtual env found: $vp"
        . $vp
        $foundVenv = $true
        break
    }
}
if (-not $foundVenv) {
    Write-Skip "No virtual env found — using system Python"
}

# ─────────────────────────────────────────────
# 3. Verify key packages installed
# ─────────────────────────────────────────────
Write-Step "3. Checking key packages"
$keyPkgs = @("fastapi", "uvicorn", "sqlalchemy", "pydantic", "alembic", "bcrypt", "apscheduler")
$missing = @()
foreach ($pkg in $keyPkgs) {
    $v = pip show $pkg 2>$null | Select-String "Version:"
    if ($v) {
        Write-Pass "$pkg $($v -replace 'Version: ', '')"
    } else {
        Write-Fail "$pkg — NOT INSTALLED"
        $missing += $pkg
    }
}

# ─────────────────────────────────────────────
# 4. Cache cleanup
# ─────────────────────────────────────────────
Write-Step "4. Cleaning Python caches"
$pycacheCount = 0
Get-ChildItem $env:PYTHONPATH -Recurse -Directory -Filter "__pycache__" -Force -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
    $pycacheCount++
}
Write-Pass "Cleared $pycacheCount __pycache__ directories"

# ─────────────────────────────────────────────
# 5. Run test suite
# ─────────────────────────────────────────────
Write-Step "5. Running test suite"
Set-Location $env:PYTHONPATH

$testResults = python -m pytest tests/ --tb=short -q 2>&1
$exitCode = $LASTEXITCODE

# Parse summary line
$summaryLine = $testResults[-1] -join ' '
if ($summaryLine -match '(\d+) passed') {
    $p = $Matches[1]
    Write-Pass "$p tests passed"
} else {
    Write-Fail "Test run issue — exit code $exitCode"
}

if ($exitCode -ne 0) {
    Write-Host "`nFailed test details:" -ForegroundColor Yellow
    $testResults | Where-Object { $_ -match 'FAILED' } | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
}

# ─────────────────────────────────────────────
# 6. Check git status
# ─────────────────────────────────────────────
Write-Step "6. Checking git status"
$status = git status --porcelain 2>$null
if ($status) {
    Write-Host "  Uncommitted changes:" -ForegroundColor Yellow
    $status | ForEach-Object { Write-Host "    $_" }
} else {
    Write-Pass "Working tree clean"
}
$branch = git rev-parse --abbrev-ref HEAD
Write-Pass "Branch: $branch"
$commits = git rev-list --count HEAD
Write-Pass "Commits: $commits"

# ─────────────────────────────────────────────
# 7. Verify server starts
# ─────────────────────────────────────────────
Write-Step "7. Quick server import check (no bind)"
try {
    $output = python -c "import sys; sys.path.insert(0, '.'); from app.main import app; print(f'App loaded: {app.title} v{app.version}')" 2>&1
    Write-Pass $output.Trim()
} catch {
    Write-Fail "Server import failed: $_"
}

# ─────────────────────────────────────────────
# 8. Check for available updates
# ─────────────────────────────────────────────
Write-Step "8. Checking for outdated packages"
$outdated = pip list --outdated --format=columns 2>$null | Select-Object -Skip 2
if ($outdated) {
    Write-Host "  Outdated packages:" -ForegroundColor Yellow
    $outdated | ForEach-Object { Write-Host "    $_" }
} else {
    Write-Pass "All packages up to date"
}

# ─────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────
Write-Step "REFRESH SUMMARY"
$total = $script:passed + $script:failed + $script:skipped
Write-Host "  Total checks : $total" -ForegroundColor White
Write-Host "  Passed       : $($script:passed)" -ForegroundColor Green
Write-Host "  Failed       : $($script:failed)" -ForegroundColor $(if ($script:failed -gt 0) { "Red" } else { "White" })
Write-Host "  Skipped      : $($script:skipped)" -ForegroundColor Yellow

if ($script:failed -eq 0) {
    Write-Host "`n✅ Environment is healthy." -ForegroundColor Green
} else {
    Write-Host "`n⚠️  $($script:failed) checks need attention." -ForegroundColor Yellow
}

# ─────────────────────────────────────────────
# 9. Open VS Code workspace (interactive)
# ─────────────────────────────────────────────
Write-Step "9. VS Code workspace"
$wsPath = "D:\ERP System\BIO_ERP\BIO_ERP.code-workspace"
if (Test-Path $wsPath -and $env:TERM_PROGRAM -ne "vscode") {
    Write-Host "  Workspace: $wsPath" -ForegroundColor Cyan
    $choice = Read-Host "  Open VS Code workspace? (y/N)"
    if ($choice -eq 'y') { code $wsPath }
} else {
    Write-Pass "Workspace ready at $wsPath"
}

Write-Host "`nDone. Refresh complete in $([math]::Round((Get-Date)-$script:startTime).TotalSeconds, 1) seconds)" -ForegroundColor Cyan