@echo off
title Synapse Launcher
cd /d D:\proyectos\SynapseCode

echo ============================================
echo  Synapse Council - Launcher v2.2
echo ============================================
echo.

REM Verificar si el servidor ya esta corriendo
netstat -ano | findstr ":8000 " | findstr LISTENING >nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] El servidor ya esta corriendo en puerto 8000
    goto START_DASHBOARD
)

REM Iniciar servidor en nueva ventana
echo [..] Iniciando servidor backend...
start "Synapse Server" cmd /k "cd /d D:\proyectos\SynapseCode && python -c "import sys; sys.path.insert(0, '.'); from backend.main import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000, workers=1)""

REM Esperar a que el servidor responda (max 30s)
echo [..] Esperando al servidor...
set /a max_wait=30
set /a waited=0

:WAIT_LOOP
ping -n 2 127.0.0.1 >nul
netstat -ano | findstr ":8000 " | findstr LISTENING >nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Servidor listo en %waited%s
    goto START_DASHBOARD
)
set /a waited=waited+2
if %waited% GEQ %max_wait% (
    echo [ERROR] El servidor no arranco en %max_wait%s
    echo         Revisa los logs en la ventana Synapse Server
    pause
    exit /b 1
)
goto WAIT_LOOP

:START_DASHBOARD
echo [OK] Abriendo Synapse Dashboard...
start "" "D:\proyectos\SynapseCode\dist\SynapseDashboard.exe"

echo.
echo ============================================
echo  Sistema iniciado correctamente.
echo  - Servidor:  http://localhost:8000
echo  - API Docs:  http://localhost:8000/docs
echo  - Dashboard: SynapseDashboard.exe
echo  - Admin:     http://localhost:8000/admin
echo ============================================
echo.
echo  Para detener el sistema:
echo    1. Cierra el Dashboard
echo    2. Cierra la ventana "Synapse Server"
echo.
