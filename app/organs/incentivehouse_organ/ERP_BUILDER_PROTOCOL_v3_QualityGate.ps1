# ERP_BUILDER_PROTOCOL_v3_QualityGate.ps1
# Incentive House ERP Builder Protocol v3.0 — Mandatory Quality Gate
# Run this before EVERY production deployment

param(
    [switch]$Strict,
    [switch]$AutoFix
)

$ERP_HOME = "D:\ERP System\BIO_ERP"
$QUALITY_SCRIPT = "$ERP_HOME\ih_erp_quality_gate_v2.py"
$REPORTS_DIR = "$ERP_HOME\reports"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ERP BUILDER PROTOCOL v3.0" -ForegroundColor Cyan
Write-Host "  MANDATORY QUALITY GATE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if quality gate script exists
if (-not (Test-Path $QUALITY_SCRIPT)) {
    Write-Host "[ERROR] Quality gate script not found: $QUALITY_SCRIPT" -ForegroundColor Red
    Write-Host "Download from: https://github.com/your-repo/ih_erp_quality_gate_v2.py" -ForegroundColor Yellow
    exit 2
}

# Run quality gate
$cmd = "python `"$QUALITY_SCRIPT`""
if ($Strict) { $cmd += " --strict" }

Write-Host "[1/3] Running quality gate..." -ForegroundColor Yellow
$start = Get-Date

$result = Invoke-Expression $cmd
$exitCode = $LASTEXITCODE

$elapsed = (Get-Date) - $start
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  QUALITY GATE COMPLETE" -ForegroundColor Cyan
Write-Host "  Duration: $($elapsed.ToString('mm\:ss'))" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Parse results
if ($exitCode -eq 0) {
    Write-Host "[PASS] All quality gates passed." -ForegroundColor Green
    Write-Host "[PASS] Production deployment APPROVED." -ForegroundColor Green
    Write-Host ""
    Write-Host "Proceeding to Phase 1: Integration Test" -ForegroundColor Green
    Write-Host "  pytest tests/ -v" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Then Phase 2: Staging Deploy" -ForegroundColor Green
    Write-Host "  docker-compose up --build" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Then Phase 3: Production Deploy" -ForegroundColor Green
    Write-Host "  Start-IH-ERP.ps1 -> START SERVER" -ForegroundColor Gray
    exit 0
} else {
    Write-Host "[FAIL] Quality gate FAILED." -ForegroundColor Red
    Write-Host "[FAIL] Production deployment BLOCKED." -ForegroundColor Red
    Write-Host ""

    # Show latest report
    $latestReport = Get-ChildItem -Path $REPORTS_DIR -Filter "quality_*.md" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latestReport) {
        Write-Host "Latest report: $($latestReport.FullName)" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "CORRECTIVE ACTIONS REQUIRED:" -ForegroundColor Red
        Write-Host ""
        Write-Host "Gate A (Static Analysis):" -ForegroundColor Cyan
        Write-Host "  ruff check --fix app/ tests/" -ForegroundColor Gray
        Write-Host "  ruff format app/ tests/" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Gate B (Security):" -ForegroundColor Cyan
        Write-Host "  Move secrets to .env, use os.environ.get()" -ForegroundColor Gray
        Write-Host "  Replace f-string SQL with parameterized queries" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Gate C (Coverage):" -ForegroundColor Cyan
        Write-Host "  pytest tests/ --cov=app --cov-report=html" -ForegroundColor Gray
        Write-Host "  Write tests for uncovered lines (see htmlcov/)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Gate D (API Docs):" -ForegroundColor Cyan
        Write-Host "  Add summary="..." to every @router decorator" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Gate E (Database):" -ForegroundColor Cyan
        Write-Host "  CREATE SCHEMA IF NOT EXISTS dbo" -ForegroundColor Gray
        Write-Host "  alembic revision --autogenerate" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Gate F (Performance):" -ForegroundColor Cyan
        Write-Host "  Profile imports: python -X importtime -c "from app.main import app"" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Gate G (Docker):" -ForegroundColor Cyan
        Write-Host "  Use python:3.12-slim, multi-stage build" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Gate H (Docs):" -ForegroundColor Cyan
        Write-Host "  Ensure README.md has: Install, Run, API, Docker, Quality Gate sections" -ForegroundColor Gray
        Write-Host ""
    }

    if ($AutoFix) {
        Write-Host "[AUTO-FIX] Attempting automatic fixes..." -ForegroundColor Yellow
        Set-Location $ERP_HOME

        # Auto-fix A: Ruff
        Write-Host "  [Auto-fix] Running ruff check --fix..." -ForegroundColor Gray
        python -m ruff check --fix app/ tests/ 2>$null
        python -m ruff format app/ tests/ 2>$null
        Write-Host "  [Auto-fix] Ruff complete." -ForegroundColor Green

        # Re-run quality gate
        Write-Host ""
        Write-Host "[RETRY] Re-running quality gate after auto-fix..." -ForegroundColor Yellow
        $result = Invoke-Expression $cmd
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[PASS] Auto-fix resolved issues. Deployment APPROVED." -ForegroundColor Green
            exit 0
        } else {
            Write-Host "[FAIL] Auto-fix insufficient. Manual intervention required." -ForegroundColor Red
            exit 1
        }
    }

    exit 1
}
