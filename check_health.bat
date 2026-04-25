@echo off
chcp 65001 >nul
title Synapse Council - Verificación de Salud
cls

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║           🔍 VERIFICACIÓN DE SALUD DEL SISTEMA              ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

:: ============================================
:: Verificar servidor API
echo [1/4] Verificando servidor API...
curl -s http://localhost:8000/health >nul 2>&1
if %errorLevel% equ 0 (
    echo    ✅ Servidor API: ACTIVO (http://localhost:8000)
    
    :: Obtener versión
    for /f "tokens=*" %%a in ('curl -s http://localhost:8000/health ^| findstr "version"') do (
        echo    📦 %%a
    )
) else (
    echo    ❌ Servidor API: INACTIVO
    echo    💡 Ejecuta: start_synapse.bat
)
echo.

:: ============================================
:: Verificar Ollama
echo [2/4] Verificando Ollama (Worker)...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorLevel% equ 0 (
    echo    ✅ Ollama: ACTIVO (http://localhost:11434)
    
    :: Contar modelos
    for /f "delims=" %%a in ('curl -s http://localhost:11434/api/tags ^| findstr /C:"name" /C:"model" ^| find /C /V ""') do (
        set MODEL_COUNT=%%a
    )
    echo    🤖 Modelos disponibles: ver listado abajo
) else (
    echo    ❌ Ollama: INACTIVO
    echo    💡 Instala Ollama: https://ollama.ai
    echo    💡 O inicia Ollama: ollama serve
)
echo.

:: ============================================
:: Verificar base de datos
echo [3/4] Verificando base de datos...
if exist "data\synapse.db" (
    for %%F in ("data\synapse.db") do (
        echo    ✅ SQLite: OK (%%~zF bytes)
    )
) else (
    echo    ⚠️  SQLite: No encontrada (se creará al iniciar)
)
echo.

:: ============================================
:: Verificar dependencias Python
echo [4/4] Verificando entorno Python...
if exist "venv\Scripts\python.exe" (
    echo    ✅ Entorno virtual: OK
    
    :: Verificar FastAPI
    venv\Scripts\python.exe -c "import fastapi; print('    ✅ FastAPI:', fastapi.__version__)" 2>nul
    if errorLevel neq 0 echo    ❌ FastAPI no instalado
    
    :: Verificar SQLAlchemy
    venv\Scripts\python.exe -c "import sqlalchemy; print('    ✅ SQLAlchemy:', sqlalchemy.__version__)" 2>nul
    if errorLevel neq 0 echo    ❌ SQLAlchemy no instalado
    
    :: Verificar httpx
    venv\Scripts\python.exe -c "import httpx; print('    ✅ httpx: OK')" 2>nul
    if errorLevel neq 0 echo    ❌ httpx no instalado
) else (
    echo    ❌ Entorno virtual no encontrado
    echo    💡 Ejecuta: INSTALL_COMPLETE.bat
)
echo.

:: ============================================
:: Resumen visual
echo ╔════════════════════════════════════════════════════════════╗
echo ║                      📊 RESUMEN                             ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

curl -s http://localhost:8000/health >nul 2>&1 && (
    echo ✅ Sistema OPERATIVO - Listo para debates
    echo.
    echo 🌐 Accesos disponibles:
    echo    • API:        http://localhost:8000
    echo    • Documentos: http://localhost:8000/docs
    echo    • Health:     http://localhost:8000/health
    echo    • Interfaz:   http://localhost:8000/static/debate_manager.html
    echo.
    echo 🚀 Para lanzar un debate:
    echo    curl -X POST http://localhost:8000/api/v1/debate/consensus/create ^
echo         -H "Content-Type: application/json" ^
echo         -d "{\"topic\":\"Tu tema aqui\",\"max_rounds\":1}"
) || (
    echo ❌ Sistema INACTIVO - Requiere atención
    echo.
    echo 🔧 Pasos para iniciar:
    echo    1. Verifica que Ollama esté ejecutándose:
echo       ollama serve
    echo.
    echo    2. Inicia el servidor:
echo       start_synapse.bat
    echo.
    echo    3. Vuelve a ejecutar esta verificación:
echo       check_health.bat
)

echo.
pause
