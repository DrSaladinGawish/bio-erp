@echo off
chcp 65001 >nul
title Incentive House ERP Launcher v5.4
color 0B

echo ============================================
echo  Incentive House ERP System Launcher v5.4
echo ============================================
echo.

set "BASE_DIR=D:\ERP System\ BIO_ERP"
cd /d "%BASE_DIR%"

:: ── CHECK PYTHON ──
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    pause
    exit /b 1
)

:: ── CHECK DATABASE ──
echo [CHECK] Database connection...
python -c "import psycopg2; conn=psycopg2.connect('dbname=bio_erp user=postgres'); cur=conn.cursor(); cur.execute('SELECT 1'); print('  OK')" 2>nul
if errorlevel 1 (
    echo [WARN] Database check failed — will retry on startup
)

:: ── CHECK DASHBOARD API ROUTES ──
echo [CHECK] Dashboard API routes...
python -c "
import requests, sys
try:
    r = requests.get('http://localhost:9001/api/v1/dashboard/summary', timeout=3)
    if r.status_code == 200:
        print('  /api/v1/dashboard/summary  OK')
    elif r.status_code == 401:
        print('  /api/v1/dashboard/summary  OK (401 = needs login)')
    else:
        print('  /api/v1/dashboard/summary  WARN (%d)' % r.status_code)
except:
    print('  /api/v1/dashboard/summary  NOT RUNNING')
" 2>nul

:: ── CHECK DASHBOARD TEMPLATE ──
echo [CHECK] Dashboard template...
python -c "
with open(r'%BASE_DIR%\app\templates\dashboard.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()
    if 'Incentive House' in content:
        print('  dashboard.html  OK (has IH section)')
    else:
        print('  dashboard.html  MISSING IH SECTION')
        print('  ^^ WARNING: Template is outdated!')
" 2>nul

:: ── CHECK ALL 8 IH MODULES ──
echo [CHECK] Incentive House modules...
for %%M in (grn cost event-budget bsc bi budget approval ops) do (
    python -c "import requests; r=requests.get('http://localhost:9001/api/v1/%%M/summary',timeout=2); print('  /api/v1/%%M/summary  %s' % ('OK' if r.status_code==200 else 'WARN'))" 2>nul
)

:: ── START SERVER ──
echo.
echo [START] Launching Incentive House ERP...
echo   Port: 9001
echo   URL:  http://localhost:9001/
echo.

start "" "http://localhost:9001/"

python app/main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Server failed to start
    pause
)
