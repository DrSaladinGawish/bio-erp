@echo off
cd /d "D:\ERP System\BIO_ERP"
echo Stopping old server...
for /f "tokens=2" %%p in ('tasklist /fi "WindowTitle eq IH-ERP" /nh 2^>nul') do taskkill /f /pid %%p 2>nul
timeout /t 3 /nobreak >nul
echo Starting server on port 9001...
start "IH-ERP" /d "D:\ERP System\BIO_ERP" cmd /c "python launcher\start_server.py"
echo Waiting for server to be ready...
:wait
timeout /t 5 /nobreak >nul
netstat -ano | findstr ":9001 " | findstr "LISTENING" >nul 2>nul
if errorlevel 1 goto wait
echo Server ready.
start "" "http://localhost:9001/login"
