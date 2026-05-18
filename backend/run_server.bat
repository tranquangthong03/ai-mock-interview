@echo off
cd /d "%~dp0"
F:/minicoda3/python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
