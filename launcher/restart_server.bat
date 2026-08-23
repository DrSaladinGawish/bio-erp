@echo off
cd /d "D:\ERP System\BIO_ERP"
taskkill /f /im python.exe 2>nul
timeout /t 3 /nobreak >nul
start "IH-ERP" cmd /c "python launcher\start_server.py"
timeout /t 5 /nobreak >nul
echo Server restarted on http://localhost:8000
