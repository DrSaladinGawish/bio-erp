@echo off
cd /d "d:\ERP System\BIO_ERP\app\organs\incentivehouse_organ"
python -m pytest tests/ --tb=line -v > pytest_full_run.txt 2>&1
echo DONE > pytest_done.flag
