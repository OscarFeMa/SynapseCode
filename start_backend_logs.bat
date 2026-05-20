@echo off
cd /d D:\proyectos\SynapseCode
.\venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
