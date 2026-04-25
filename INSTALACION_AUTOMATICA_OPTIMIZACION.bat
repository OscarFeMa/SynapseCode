@echo off
REM ========================================
REM INSTALACION AUTOMATICA DE OPTIMIZACION
REM Synapse Council - Worker Optimization
REM ========================================
REM
RESTE SCRIPT DEBE EJECUTARSE EN EL WORKER (192.168.1.43)
REM EJECUTAR COMO ADMINISTRADOR
REM ========================================

echo.
echo ========================================
echo INSTALACION AUTOMATICA DE OPTIMIZACION
echo Synapse Council - Worker Optimization
echo ========================================
echo.

REM Verificar privilegios de administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Este script requiere privilegios de administrador.
    echo Por favor, haz clic derecho y selecciona "Ejecutar como administrador".
    pause
    exit /b 1
)

echo [1/6] Optimizando memoria del sistema...
echo.

echo Deteniendo servicios innecesarios...
sc stop "SysMain" 2>nul
sc config "SysMain" start= disabled 2>nul
sc stop "WSearch" 2>nul
sc config "WSearch" start= disabled 2>nul
sc stop "DiagTrack" 2>nul
sc config "DiagTrack" start= disabled 2>nul
sc stop "XblAuthManager" 2>nul
sc config "XblAuthManager" start= disabled 2>nul
sc stop "XblGameSave" 2>nul
sc config "XblGameSave" start= disabled 2>nul
sc stop "XboxNetApiSvc" 2>nul
sc config "XboxNetApiSvc" start= disabled 2>nul
sc stop "Spooler" 2>nul
sc config "Spooler" start= disabled 2>nul
echo Servicios deshabilitados.
echo.

echo Cerrando procesos que consumen memoria...
taskkill /F /IM chrome.exe 2>nul
taskkill /F /IM firefox.exe 2>nul
taskkill /F /IM msedge.exe 2>nul
taskkill /F /IM brave.exe 2>nul
taskkill /F /IM MicrosoftEdge.exe 2>nul
taskkill /F /IM RuntimeBroker.exe 2>nul
taskkill /F /IM ShellExperienceHost.exe 2>nul
taskkill /F /IM OneDrive.exe 2>nul
echo Procesos cerrados.
echo.

echo Limpiando archivos temporales...
del /F /S /Q %TEMP%\* 2>nul
del /F /S /Q C:\Windows\Temp\* 2>nul
powershell -Command "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
echo Archivos temporales limpiados.
echo.

echo [2/6] Configurando memoria virtual...
wmic pagefileset where "name='C:\\pagefile.sys'" set InitialSize=16384,MaximumSize=32768
echo Memoria virtual configurada (16GB min, 32GB max).
echo.

echo [3/6] Configurando variables de entorno para Ollama GPU...
setx OLLAMA_NUM_GPU 999 /M
setx OLLAMA_GPU_OVERHEAD 0 /M
setx OLLAMA_LOAD_TIMEOUT 5m /M
setx OLLAMA_KEEP_ALIVE -1 /M
setx OLLAMA_MAX_QUEUE 4 /M
setx OLLAMA_MAX_LOADED_MODELS 2 /M
setx OLLAMA_FLASH_ATTENTION 1 /M
setx OLLAMA_KV_CACHE_TYPE f16 /M
setx CUDA_VISIBLE_DEVICES 0 /M
echo Variables de entorno configuradas.
echo.

echo [4/6] Verificando GPU NVIDIA...
nvidia-smi >nul 2>&1
if %errorlevel% neq 0 (
    echo [ADVERTENCIA] No se detecta GPU NVIDIA.
    echo Se usara CPU para inferencia.
) else (
    echo GPU NVIDIA detectada.
    echo.
    echo --- Informacion de GPU ---
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
)
echo.

echo [5/6] Reiniciando Ollama con nueva configuracion...
taskkill /F /IM ollama.exe 2>nul
timeout /t 3 /nobreak >nul
start "" "C:\Users\maked\AppData\Local\Programs\Ollama\ollama.exe" serve
timeout /t 5 /nobreak >nul
echo Ollama reiniciado.
echo.

echo [6/6] Descargando modelos optimizados...
echo.
echo Descargando llama3:8b (esto puede tardar varios minutos)...
ollama pull llama3:8b
echo.

echo Descargando qwen2.5:7b...
ollama pull qwen2.5:7b
echo.

echo Descargando mistral:7b...
ollama pull mistral:7b
echo.

echo Verificando modelos descargados...
ollama list
echo.

echo ========================================
echo OPTIMIZACION COMPLETADA
echo ========================================
echo.
echo Cambios realizados:
echo - Servicios innecesarios deshabilitados
echo - Procesos que consumen memoria cerrados
echo - Archivos temporales eliminados
echo - Memoria virtual aumentada a 16-32GB
echo - Ollama configurado para usar GPU
echo - Modelos grandes descargados:
echo   * llama3:8b
echo   * qwen2.5:7b
echo   * mistral:7b
echo.
echo Presiona cualquier tecla para salir...
pause >nul
