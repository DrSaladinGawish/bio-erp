@echo off
cd /d "D:\ERP System\BIO_ERP"
set PYTHONPATH=D:\ERP System\BIO_ERP
echo Starting BIO-ERP on port 8000...
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
