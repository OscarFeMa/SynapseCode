@echo off
echo =========================================
echo  SYNAPSE COUNCIL v2.0 - NODO MASTER
echo =========================================
echo.
echo Comprobando entorno virtual...
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] No se encontro el entorno virtual. Sigue los pasos del Manual_de_Uso_Master.md para instalarlo la primera vez.
    pause
    exit /b
)

echo 1. Iniciando Backend (FastAPI) en puerto 8000...
start "Synapse Backend (Master)" cmd /k "call venv\Scripts\activate.bat && set PYTHONPATH=. && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1"

echo 2. Iniciando Frontend (React)...
if not exist "frontend\node_modules" (
    echo [AVISO] Node modules no encontrados. Asegurate de haber ejecutado 'npm install' en la carpeta frontend.
)
cd frontend
start "Synapse Frontend" cmd /k "npm run dev"

echo.
echo =========================================
echo Todo iniciado correctamente.
echo La interfaz web esta en: http://localhost:5173
echo =========================================
echo.
echo Puedes cerrar esta ventana negra.
pause
