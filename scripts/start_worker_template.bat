@echo off
chcp 65001 >nul
title Synapse Council - Worker Node
cls

echo ╔════════════════════════════════════════════════════════════╗
echo ║     SYNAPSE COUNCIL v2.0 - WORKER NODE                   ║
echo ║     Motores Locales (Ollama/LM Studio/Jan.ai)            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Verificar motores locales
echo [1/4] Verificando motores locales...

curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% == 0 (
    echo   [OK] Ollama detectado en puerto 11434
) else (
    echo   [  ] Ollama no detectado
)

curl -s http://localhost:1234/v1/models >nul 2>&1
if %errorlevel% == 0 (
    echo   [OK] LM Studio detectado en puerto 1234
) else (
    echo   [  ] LM Studio no detectado
)

curl -s http://localhost:1337/v1/models >nul 2>&1
if %errorlevel% == 0 (
    echo   [OK] Jan.ai detectado en puerto 1337
) else (
    echo   [  ] Jan.ai no detectado
)

echo.

REM Verificar entorno virtual
if not exist "venv\Scripts\activate.bat" (
    echo [2/4] Creando entorno virtual...
    python -m venv venv
)

echo [2/4] Activando entorno virtual...
call venv\Scripts\activate.bat

echo [3/4] Verificando dependencias...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias...
    pip install -r backend\requirements.txt
)

echo.
echo [4/4] Iniciando Worker Node en puerto 8001...
echo ========================================
echo Este Worker proporcionara motores locales al Master
echo.
echo Accesos:
echo   - API:      http://localhost:8001
echo   - Health:   http://localhost:8001/health
echo   - Peers:    http://localhost:8001/api/v1/network/peers
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

python backend\main.py

if errorlevel 1 (
    echo.
    echo [ERROR] El servidor termino con errores.
    pause
)
