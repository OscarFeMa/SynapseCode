@echo off
chcp 65001 >nul
title Synapse Council - Configuracion Master
cls

echo ╔════════════════════════════════════════════════════════════╗
echo ║  CONFIGURACION AUTOMATICA - SYNAPSE MASTER                ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo Este script configurara este PC como MASTER (usa OpenRouter/Web Agent)
echo El otro PC debera tener Ollama/LM Studio corriendo (WORKER)
echo.
pause
cls

echo [1/5] Detectando IP local...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set "LOCAL_IP=%%a"
    set "LOCAL_IP=!LOCAL_IP: =!"
    echo IP Local: !LOCAL_IP!
    goto :ip_done
)
:ip_done
echo.

echo [2/5] Configurando archivo .env para MASTER...
(
echo # Auto-configurado por Synapse Council
echo NODE_ROLE=MASTER
echo PORT=8000
echo HOST=0.0.0.0
echo.
echo # --- Worker Configuration ---
echo # IP del Worker ^(se actualizara automaticamente via discovery^)
echo WORKER_HOST=
echo WORKER_OLLAMA_PORT=11434
echo WORKER_LM_STUDIO_PORT=1234
echo WORKER_JAN_PORT=1337
echo.
echo # --- API Keys (rellenar si se tienen) ---
echo # OPENROUTER_API_KEY=tu_api_key_aqui
echo.
echo # --- Supabase (Opcional, para elevacion a nube) ---
echo # SUPABASE_URL=tu_url
echo # SUPABASE_ANON_KEY=tu_key
echo.
echo # --- Features del Master ---
echo WEB_AGENT_ENABLED=true
echo MAX_CONCURRENT_SESSIONS=3
echo DISCOVERY_PORT=54321
echo DISCOVERY_INTERVAL=5
) > .env

echo [OK] Archivo .env creado
echo.

echo [3/5] Verificando entorno virtual...
if not exist "venv\Scripts\activate.bat" (
    echo Creando entorno virtual...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear entorno virtual
        pause
        exit /b 1
    )
)
echo [OK] Entorno virtual listo
echo.

echo [4/5] Instalando dependencias...
call venv\Scripts\activate.bat >nul
pip install -q -r backend\requirements.txt
if errorlevel 1 (
    echo [ADVERTENCIA] Algunas dependencias no se instalaron correctamente
    echo Intentando instalacion individual...
    pip install fastapi uvicorn httpx sqlalchemy aiosqlite pydantic-settings structlog
)
echo [OK] Dependencias instaladas
echo.

echo [5/5] Verificando estructura...
if not exist "data" mkdir data
echo [OK] Carpetas verificadas
echo.

echo ╔════════════════════════════════════════════════════════════╗
echo ║  CONFIGURACION COMPLETADA                                ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo Este PC esta configurado como: MASTER
echo.
echo Proximos pasos:
echo 1. Asegurate de que el otro PC (WORKER) tenga:
echo    - Ollama o LM Studio corriendo
echo    - Synapse Council configurado como WORKER
echo    - Ambos en la misma red local
echo.
echo 2. Para iniciar el Master:
echo    start_synapse.bat
echo.
echo 3. Verificar conexion:
echo    curl http://localhost:8000/health
echo.
echo 4. El Master detectara automaticamente al Worker via UDP
echo.
pause
