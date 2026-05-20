@echo off
cd /d D:\proyectos\SynapseCode
start /min cmd /c ".\venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"
timeout /t 5 /nobreak >nul
start "" "https://synapsecode.org"
