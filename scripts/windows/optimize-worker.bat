@echo off
REM ========================================
REM OPTIMIZACION DE MEMORIA PARA WORKER
REM Synapse Council - GPU & RAM Optimization
REM ========================================

echo.
echo ========================================
echo OPTIMIZACION DE MEMORIA PARA WORKER
echo Synapse Council - GPU & RAM Optimization
echo ========================================
echo.

REM Verificar privilegios de administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Este script requiere privilegios de administrador.
    echo Por favor, ejecuta como Administrador.
    pause
    exit /b 1
)

echo [1/8] Informacion del sistema...
echo.
echo --- RAM Total ---
systeminfo | findstr /C:"Total Physical Memory"
echo.
echo --- GPU Disponible ---
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>nul
if %errorlevel% neq 0 (
    echo [ADVERTENCIA] No se detecta GPU NVIDIA o nvidia-smi no esta instalado.
    echo Se usara CPU para inferencia.
) else (
    echo GPU NVIDIA detectada.
)
echo.

echo [2/8] Deteniendo servicios innecesarios...
echo Deteniendo Superfetch/SysMain...
sc stop "SysMain" 2>nul
sc config "SysMain" start= disabled 2>nul

echo Deteniendo Windows Search...
sc stop "WSearch" 2>nul
sc config "WSearch" start= disabled 2>nul

echo Deteniendo Telemetria de Windows...
sc stop "DiagTrack" 2>nul
sc config "DiagTrack" start= disabled 2>nul

echo Deteniendo servicios Xbox...
sc stop "XblAuthManager" 2>nul
sc config "XblAuthManager" start= disabled 2>nul
sc stop "XblGameSave" 2>nul
sc config "XblGameSave" start= disabled 2>nul
sc stop "XboxNetApiSvc" 2>nul
sc config "XboxNetApiSvc" start= disabled 2>nul

echo Deteniendo Print Spooler (si no se usa impresora)...
sc stop "Spooler" 2>nul
sc config "Spooler" start= disabled 2>nul

echo Servicios innecesarios detenidos y deshabilitados.
echo.

echo [3/8] Limpiando procesos que consumen memoria...
echo Cerrando navegadores web...
taskkill /F /IM chrome.exe 2>nul
taskkill /F /IM firefox.exe 2>nul
taskkill /F /IM msedge.exe 2>nul
taskkill /F /IM brave.exe 2>nul

echo Cerrando aplicaciones de Microsoft Store...
taskkill /F /IM MicrosoftEdge.exe 2>nul
taskkill /F /IM RuntimeBroker.exe 2>nul
taskkill /F /IM ShellExperienceHost.exe 2>nul

echo Cerrando OneDrive (si no se usa)...
taskkill /F /IM OneDrive.exe 2>nul

echo Procesos innecesarios cerrados.
echo.

echo [4/8] Limpiando archivos temporales...
echo Limpiando carpeta Temp...
del /F /S /Q %TEMP%\* 2>nul
del /F /S /Q C:\Windows\Temp\* 2>nul

echo Limpiando Papelera de Reciclaje...
powershell -Command "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"

echo Archivos temporales limpiados.
echo.

echo [5/8] Configurando variables de entorno para Ollama...
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

echo [6/8] Configurando memoria virtual...
echo Aumentando pagina de memoria virtual...
wmic pagefileset where "name='C:\\pagefile.sys'" set InitialSize=16384,MaximumSize=32768
echo Memoria virtual configurada (16GB min, 32GB max).
echo.

echo [7/8] Reiniciando servicio Ollama con nueva configuracion...
echo Deteniendo Ollama...
taskkill /F /IM ollama.exe 2>nul
timeout /t 3 /nobreak >nul

echo Iniciando Ollama...
start "" "C:\Users\maked\AppData\Local\Programs\Ollama\ollama.exe" serve
timeout /t 5 /nobreak >nul

echo Verificando que Ollama este corriendo...
curl -s http://localhost:11434/api/tags >nul
if %errorlevel% equ 0 (
    echo Ollama iniciado correctamente.
) else (
    echo [ADVERTENCIA] Ollama no respondio. Verifica la instalacion.
)
echo.

echo [8/8] Verificando memoria disponible...
echo.
echo --- Memoria RAM Libre ---
wmic OS get FreePhysicalMemory /Value
echo.
echo --- GPU Libre ---
nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>nul
if %errorlevel% neq 0 (
    echo No disponible (sin GPU NVIDIA)
)
echo.

echo ========================================
echo OPTIMIZACION COMPLETADA
echo ========================================
echo.
echo Cambios realizados:
echo - Servicios innecesarios deshabilitados
echo - Procesos que consumen memoria cerrados
echo - Archivos temporales eliminados
echo - Ollama configurado para usar GPU
echo - Memoria virtual aumentada
echo.
echo Presiona cualquier tecla para salir...
pause >nul
