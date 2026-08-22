@echo off
cd /d "D:\ERP System\BIO_ERP"
echo Stopping old server...
for /f "tokens=2" %%p in ('tasklist /fi "WindowTitle eq IH-ERP" /nh 2^>nul') do taskkill /f /pid %%p 2>nul
timeout /t 3 /nobreak >nul
echo Starting server on port 8000...
start "IH-ERP" /d "D:\ERP System\BIO_ERP" cmd /c "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"
echo Waiting for server to be ready...
:wait
timeout /t 5 /nobreak >nul
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul 2>nul
if errorlevel 1 goto wait
echo Server ready.
start "" "http://localhost:8000/eba"
