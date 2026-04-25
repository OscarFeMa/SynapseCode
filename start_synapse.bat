@echo off
chcp 65001 >nul
title Synapse Council - Master Node
cls

echo ╔════════════════════════════════════════════════════════════╗
echo ║     SYNAPSE COUNCIL v2.0 - MASTER NODE                    ║
echo ║     Orquestador Hibrido (OpenRouter + Web Agent)         ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Verificar entorno virtual
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] No se encontro entorno virtual.
    echo Creando entorno virtual...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
)

echo [1/4] Activando entorno virtual...
call venv\Scripts\activate.bat

echo [2/4] Verificando dependencias...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias...
    pip install -r backend\requirements.txt
)

echo [3/4] Ejecutando diagnostico de red...
python scripts\network_diagnostic.py --target %WORKER_IP% 2>nul || echo Diagnostico opcional omitido

echo.
echo [4/4] Iniciando Master Node en puerto 8000...
echo ========================================
echo Accesos:
echo   - API:      http://localhost:8000
echo   - Docs:     http://localhost:8000/docs
echo   - Health:   http://localhost:8000/health
echo   - Frontend: http://localhost:5173 (si esta compilado)
echo ========================================
echo.
echo Presiona Ctrl+C para detener
echo.

REM Detectar IP local para mostrarla
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set LOCAL_IP=%%a
    goto :found_ip
)
:found_ip
echo IP Local: %LOCAL_IP%
echo.

set PYTHONPATH=%CD%;%PYTHONPATH%
python backend\main.py

if errorlevel 1 (
    echo.
    echo [ERROR] El servidor termino con errores.
    pause
)
