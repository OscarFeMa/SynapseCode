@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: ============================================
:: Synapse Council v2.0 - Instalador Completo
:: Master + Worker en una sola PC
:: ============================================

title Instalador Synapse Council v2.0

color 0B
cls

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                                                            ║
echo ║           🧠 SYNAPSE COUNCIL v2.0 - Instalador            ║
echo ║                                                            ║
echo ║   Razonamiento Colectivo Multi-Agente con Consenso          ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

:: ============================================
:: Verificar privilegios de administrador
:: ============================================
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ⚠️  Se requieren privilegios de Administrador
    echo    Por favor, ejecuta este script como Administrador
    pause
    exit /b 1
)

echo ✅ Privilegios de administrador verificados
echo.

:: ============================================
:: Configuración de rutas
:: ============================================
set "INSTALL_DIR=%~dp0"
set "VENV_DIR=%INSTALL_DIR%venv"
set "DATA_DIR=%INSTALL_DIR%data"
set "LOGS_DIR=%INSTALL_DIR%logs"

echo 📁 Directorio de instalación: %INSTALL_DIR%
echo.

:: ============================================
:: Crear estructura de directorios
:: ============================================
echo [1/8] Creando estructura de directorios...
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"
if not exist "%DATA_DIR%\debates" mkdir "%DATA_DIR%\debates"
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"
if not exist "%INSTALL_DIR%\web_interface" mkdir "%INSTALL_DIR%\web_interface"

echo    ✅ data\debates
echo    ✅ logs
echo    ✅ web_interface
echo.

:: ============================================
:: Verificar Python
:: ============================================
echo [2/8] Verificando Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ Python no está instalado o no está en PATH
    echo    Descarga Python desde: https://python.org
    pause
    exit /b 1
)

for /f "tokens=*" %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
echo    ✅ %PYTHON_VERSION%
echo.

:: ============================================
:: Verificar Git (opcional pero recomendado)
:: ============================================
echo [3/8] Verificando Git...
git --version >nul 2>&1
if %errorLevel% equ 0 (
    for /f "tokens=*" %%a in ('git --version') do set GIT_VERSION=%%a
    echo    ✅ %GIT_VERSION%
) else (
    echo    ⚠️  Git no encontrado (opcional para actualizaciones)
)
echo.

:: ============================================
:: Crear entorno virtual
:: ============================================
echo [4/8] Configurando entorno virtual...
if exist "%VENV_DIR%" (
    echo    ℹ️  Entorno virtual existente encontrado
    choice /C SN /N /M "    ¿Recrear entorno virtual? (S/N): "
    if !errorLevel! equ 1 (
        rmdir /S /Q "%VENV_DIR%"
        echo    🗑️  Entorno anterior eliminado
    )
)

if not exist "%VENV_DIR%" (
    echo    📦 Creando nuevo entorno virtual...
    python -m venv "%VENV_DIR%"
    if !errorLevel! neq 0 (
        echo    ❌ Error creando entorno virtual
        pause
        exit /b 1
    )
    echo    ✅ Entorno virtual creado
) else (
    echo    ✅ Usando entorno virtual existente
)
echo.

:: ============================================
:: Instalar dependencias
:: ============================================
echo [5/8] Instalando dependencias...
set "PIP=%VENV_DIR%\Scripts\pip.exe"

:: Actualizar pip
"%PIP%" install --upgrade pip -q

:: Instalar requirements
if exist "%INSTALL_DIR%\backend\requirements.txt" (
    echo    📦 Instalando desde requirements.txt...
    "%PIP%" install -r "%INSTALL_DIR%\backend\requirements.txt" -q
    if !errorLevel! neq 0 (
        echo    ❌ Error instalando dependencias
        pause
        exit /b 1
    )
    echo    ✅ Dependencias instaladas
) else (
    echo    ⚠️  requirements.txt no encontrado
)

:: Instalar playwright (opcional para Web Agent)
echo    🎭 Verificando Playwright...
"%VENV_DIR%\Scripts\python.exe" -m playwright install chromium >nul 2>&1
echo    ✅ Playwright chromium instalado
echo.

:: ============================================
:: Crear archivo .env si no existe
:: ============================================
echo [6/8] Configurando variables de entorno...
if not exist "%INSTALL_DIR%\.env" (
    echo    📝 Creando archivo .env...
    (
        echo # ============================================
        echo # Synapse Council v2.0 - Configuración
echo # ============================================
        echo.
        echo # Node Configuration
echo NODE_ROLE=master
echo NODE_ID=master-001
echo.
        echo # Master Configuration
echo MASTER_HOST=localhost
echo MASTER_PORT=8000
echo MASTER_IP=192.168.1.100
echo.
        echo # Worker Configuration (desactivado en modo standalone)
echo WORKER_HOST=localhost
echo WORKER_PORT=8001
echo WORKER_OLLAMA_PORT=11434
echo.
        echo # Ollama Configuration
echo OLLAMA_BASE_URL=http://localhost:11434
echo.
        echo # OpenRouter (opcional - para APIs comerciales)
echo # OPENROUTER_API_KEY=sk-or-v1-...
echo # OPENROUTER_DEFAULT_MODEL=anthropic/claude-3.5-sonnet
echo.
        echo # Supabase (opcional - para cloud sync)
echo # SUPABASE_URL=https://your-project.supabase.co
echo # SUPABASE_ANON_KEY=your-anon-key
echo # SUPABASE_ENABLED=true
echo.
        echo # Security
echo SECRET_KEY=your-secret-key-here-change-in-production
echo.
        echo # Database
echo DATABASE_URL=sqlite+aiosqlite:///./data/synapse.db
echo.
        echo # Logging
echo LOG_LEVEL=INFO
echo LOG_FORMAT=json
    ) > "%INSTALL_DIR%\.env"
    echo    ✅ Archivo .env creado (editar con tus credenciales)
) else (
    echo    ℹ️  Archivo .env ya existe
)
echo.

:: ============================================
:: Configurar base de datos SQLite
:: ============================================
echo [7/8] Configurando base de datos...
set "PYTHON=%VENV_DIR%\Scripts\python.exe"

"%PYTHON%" -c "
import sys
sys.path.insert(0, '.')
from backend.database.local_db import init_db
import asyncio
asyncio.run(init_db())
" >nul 2>&1

if %errorLevel% equ 0 (
    echo    ✅ Base de datos SQLite inicializada
) else (
    echo    ⚠️  No se pudo inicializar la base de datos (se creará automáticamente al iniciar)
)
echo.

:: ============================================
:: Crear accesos directos
:: ============================================
echo [8/8] Creando accesos directos...

:: Acceso directo al escritorio (opcional)
choice /C SN /N /M "¿Crear acceso directo en el escritorio? (S/N): "
if %errorLevel% equ 1 (
    set "DESKTOP=%USERPROFILE%\Desktop"
    (
        echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
        echo sLinkFile = "%DESKTOP%\Synapse Council.lnk"
        echo Set oLink = oWS.CreateShortcut^(sLinkFile^)
        echo oLink.TargetPath = "%INSTALL_DIR%\start_synapse.bat"
        echo oLink.WorkingDirectory = "%INSTALL_DIR%"
        echo oLink.IconLocation = "%SystemRoot%\System32\SHELL32.dll,14"
        echo oLink.Description = "Synapse Council - Razonamiento Multi-Agente"
        echo oLink.Save
    ) > "%TEMP%\CreateShortcut.vbs"
    cscript //nologo "%TEMP%\CreateShortcut.vbs"
    del "%TEMP%\CreateShortcut.vbs"
    echo    ✅ Acceso directo creado en el escritorio
)
echo.

:: ============================================
:: Verificación final
:: ============================================
echo ╔════════════════════════════════════════════════════════════╗
echo ║                    ✅ INSTALACIÓN COMPLETA                  ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo 📋 Resumen de instalación:
echo    • Entorno virtual: %VENV_DIR%
echo    • Base de datos: %DATA_DIR%\synapse.db
echo    • Logs: %LOGS_DIR%
echo    • Configuración: %INSTALL_DIR%\.env
echo.
echo 🚀 Próximos pasos:
echo    1. Edita .env con tu configuración (SUPABASE_URL, etc.)
echo    2. Instala Ollama: https://ollama.ai
echo    3. Descarga modelos: ollama pull llama3:8b
echo    4. Ejecuta: start_synapse.bat
echo    5. Abre: http://localhost:8000/static/debate_manager.html
echo.
echo 📖 Documentación:
echo    • README.md - Guía completa
echo    • HISTORY.md - Evolución del proyecto
echo    • API docs: http://localhost:8000/docs (al iniciar)
echo.
echo 💡 Comandos útiles:
echo    • Iniciar: start_synapse.bat
echo    • Verificar: check_health.bat
echo    • Instalar modelos: install_models.bat
echo.
pause
