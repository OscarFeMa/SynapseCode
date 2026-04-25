@echo off
REM ========================================
REM OPTIMIZACION SIMPLE DE WORKER
REM Synapse Council - Simple Worker Optimization
REM ========================================
REM
ESTE SCRIPT DEBE EJECUTARSE EN EL WORKER (192.168.1.43)
EJECUTAR COMO ADMINISTRADOR
========================================

set LOG_FILE=C:\Users\maked\Desktop\optimizacion_log.txt

echo.
echo ========================================
echo OPTIMIZACION SIMPLE DE WORKER
echo Synapse Council - Simple Worker Optimization
echo ========================================
echo.

echo [%date% %time%] Iniciando optimizacion... > %LOG_FILE%
echo [%date% %time%] Iniciando optimizacion...

REM Verificar privilegios de administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Este script requiere privilegios de administrador.
    echo [%date% %time%] ERROR: Sin privilegios de administrador >> %LOG_FILE%
    pause
    exit /b 1
)
echo [%date% %time%] Privilegios de administrador verificados. >> %LOG_FILE%
echo [OK] Privilegios de administrador verificados.
echo.

echo [1/8] Informacion del sistema...
echo [%date% %time%] Obteniendo informacion del sistema... >> %LOG_FILE%
systeminfo | findstr /C:"Total Physical Memory" >> %LOG_FILE%
systeminfo | findstr /C:"Total Physical Memory"
echo.

echo [2/8] Verificando GPU...
echo [%date% %time%] Verificando GPU... >> %LOG_FILE%
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv >> %LOG_FILE% 2>&1
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] ADVERTENCIA: No se detecta GPU NVIDIA >> %LOG_FILE%
    echo [ADVERTENCIA] No se detecta GPU NVIDIA.
) else (
    echo [%date% %time%] GPU NVIDIA detectada >> %LOG_FILE%
    echo [OK] GPU NVIDIA detectada.
)
echo.

echo [3/8] Deteniendo servicios innecesarios...
echo [%date% %time%] Deteniendo servicios... >> %LOG_FILE%
sc stop "SysMain" >> %LOG_FILE% 2>&1
sc config "SysMain" start= disabled >> %LOG_FILE% 2>&1
sc stop "WSearch" >> %LOG_FILE% 2>&1
sc config "WSearch" start= disabled >> %LOG_FILE% 2>&1
sc stop "DiagTrack" >> %LOG_FILE% 2>&1
sc config "DiagTrack" start= disabled >> %LOG_FILE% 2>&1
sc stop "XblAuthManager" >> %LOG_FILE% 2>&1
sc config "XblAuthManager" start= disabled >> %LOG_FILE% 2>&1
sc stop "XblGameSave" >> %LOG_FILE% 2>&1
sc config "XblGameSave" start= disabled >> %LOG_FILE% 2>&1
sc stop "XboxNetApiSvc" >> %LOG_FILE% 2>&1
sc config "XboxNetApiSvc" start= disabled >> %LOG_FILE% 2>&1
echo [%date% %time%] Servicios detenidos >> %LOG_FILE%
echo [OK] Servicios detenidos.
echo.

echo [4/8] Cerrando procesos que consumen memoria...
echo [%date% %time%] Cerrando procesos... >> %LOG_FILE%
taskkill /F /IM chrome.exe >> %LOG_FILE% 2>&1
taskkill /F /IM firefox.exe >> %LOG_FILE% 2>&1
taskkill /F /IM msedge.exe >> %LOG_FILE% 2>&1
taskkill /F /IM brave.exe >> %LOG_FILE% 2>&1
taskkill /F /IM MicrosoftEdge.exe >> %LOG_FILE% 2>&1
taskkill /F /IM RuntimeBroker.exe >> %LOG_FILE% 2>&1
taskkill /F /IM ShellExperienceHost.exe >> %LOG_FILE% 2>&1
taskkill /F /IM OneDrive.exe >> %LOG_FILE% 2>&1
echo [%date% %time%] Procesos cerrados >> %LOG_FILE%
echo [OK] Procesos cerrados.
echo.

echo [5/8] Limpiando archivos temporales...
echo [%date% %time%] Limpiando archivos temporales... >> %LOG_FILE%
del /F /S /Q %TEMP%\* >> %LOG_FILE% 2>&1
del /F /S /Q C:\Windows\Temp\* >> %LOG_FILE% 2>&1
powershell -Command "Clear-RecycleBin -Force -ErrorAction SilentlyContinue" >> %LOG_FILE% 2>&1
echo [%date% %time%] Archivos temporales limpiados >> %LOG_FILE%
echo [OK] Archivos temporales limpiados.
echo.

echo [6/8] Configurando variables de entorno para Ollama...
echo [%date% %time%] Configurando variables de entorno... >> %LOG_FILE%
setx OLLAMA_NUM_GPU 999 /M >> %LOG_FILE% 2>&1
setx OLLAMA_GPU_OVERHEAD 0 /M >> %LOG_FILE% 2>&1
setx OLLAMA_LOAD_TIMEOUT 5m /M >> %LOG_FILE% 2>&1
setx OLLAMA_KEEP_ALIVE -1 /M >> %LOG_FILE% 2>&1
setx OLLAMA_MAX_QUEUE 4 /M >> %LOG_FILE% 2>&1
setx OLLAMA_MAX_LOADED_MODELS 2 /M >> %LOG_FILE% 2>&1
setx OLLAMA_FLASH_ATTENTION 1 /M >> %LOG_FILE% 2>&1
setx OLLAMA_KV_CACHE_TYPE f16 /M >> %LOG_FILE% 2>&1
setx CUDA_VISIBLE_DEVICES 0 /M >> %LOG_FILE% 2>&1
echo [%date% %time%] Variables de entorno configuradas >> %LOG_FILE%
echo [OK] Variables de entorno configuradas.
echo.

echo [7/8] Reiniciando Ollama...
echo [%date% %time%] Reiniciando Ollama... >> %LOG_FILE%
taskkill /F /IM ollama.exe >> %LOG_FILE% 2>&1
timeout /t 3 /nobreak >nul
start "" "C:\Users\maked\AppData\Local\Programs\Ollama\ollama.exe" serve
timeout /t 5 /nobreak >nul
echo [%date% %time%] Ollama reiniciado >> %LOG_FILE%
echo [OK] Ollama reiniciado.
echo.

echo [8/8] Descargando modelos...
echo [%date% %time%] Descargando llama3:8b... >> %LOG_FILE%
echo Descargando llama3:8b (esto puede tardar varios minutos)...
ollama pull llama3:8b >> %LOG_FILE% 2>&1
echo [%date% %time%] llama3:8b descargado >> %LOG_FILE%
echo [OK] llama3:8b descargado.
echo.

echo [%date% %time%] Descargando qwen2.5:7b... >> %LOG_FILE%
echo Descargando qwen2.5:7b...
ollama pull qwen2.5:7b >> %LOG_FILE% 2>&1
echo [%date% %time%] qwen2.5:7b descargado >> %LOG_FILE%
echo [OK] qwen2.5:7b descargado.
echo.

echo [%date% %time%] Descargando mistral:7b... >> %LOG_FILE%
echo Descargando mistral:7b...
ollama pull mistral:7b >> %LOG_FILE% 2>&1
echo [%date% %time%] mistral:7b descargado >> %LOG_FILE%
echo [OK] mistral:7b descargado.
echo.

echo [%date% %time%] Verificando modelos... >> %LOG_FILE%
ollama list >> %LOG_FILE% 2>&1
echo [%date% %time%] Modelos disponibles: >> %LOG_FILE%
ollama list
echo.

echo [%date% %time%] Verificando memoria libre... >> %LOG_FILE%
wmic OS get FreePhysicalMemory /Value >> %LOG_FILE%
echo [%date% %time%] Memoria RAM libre: >> %LOG_FILE%
wmic OS get FreePhysicalMemory /Value
echo.

echo ========================================
echo OPTIMIZACION COMPLETADA
echo ========================================
echo.
echo [%date% %time%] Optimizacion completada >> %LOG_FILE%
echo Log guardado en: %LOG_FILE%
echo.
echo Presiona cualquier tecla para salir...
pause >nul
