@echo off
REM Script de optimización de memoria para Worker Synapse
REM Libera recursos y configura el sistema para inferencia de modelos

echo ========================================
echo OPTIMIZACION DE MEMORIA PARA WORKER
echo ========================================
echo.

echo [1/6] Deteniendo servicios innecesarios...
sc stop "SysMain" 2>nul
sc stop "DiagTrack" 2>nul
sc stop "WSearch" 2>nul
sc stop "XblAuthManager" 2>nul
sc stop "XblGameSave" 2>nul
sc stop "XboxNetApiSvc" 2>nul
echo Servicios innecesarios detenidos.
echo.

echo [2/6] Limpiando memoria RAM...
powershell -Command "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
powershell -Command "Get-Process | Where-Object {$_.ProcessName -match 'chrome|firefox|edge|msedge'} | Stop-Process -Force -ErrorAction SilentlyContinue"
echo Memoria RAM limpiada.
echo.

echo [3/6] Configurando Ollama para usar GPU...
set OLLAMA_NUM_GPU=999
set OLLAMA_GPU_OVERHEAD=0
set OLLAMA_LOAD_TIMEOUT=5m
set OLLAMA_KEEP_ALIVE=-1
set OLLAMA_MAX_QUEUE=4
set OLLAMA_MAX_LOADED_MODELS=2
setx OLLAMA_NUM_GPU 999
setx OLLAMA_GPU_OVERHEAD 0
setx OLLAMA_LOAD_TIMEOUT 5m
setx OLLAMA_KEEP_ALIVE -1
setx OLLAMA_MAX_QUEUE 4
setx OLLAMA_MAX_LOADED_MODELS 2
echo Ollama configurado para usar GPU.
echo.

echo [4/6] Verificando disponibilidad de GPU...
nvidia-smi --query-gpu=memory.total,memory.free --format=csv,noheader,nounits 2>nul
if %errorlevel% neq 0 (
    echo No se detecta GPU NVIDIA. Se usara CPU.
) else (
    echo GPU NVIDIA detectada y disponible.
)
echo.

echo [5/6] Reiniciando servicio Ollama con nueva configuracion...
taskkill /F /IM ollama.exe 2>nul
timeout /t 3 /nobreak >nul
start "" "C:\Users\maked\AppData\Local\Programs\Ollama\ollama.exe" serve
timeout /t 5 /nobreak >nul
echo Servicio Ollama reiniciado.
echo.

echo [6/6] Verificando modelos disponibles...
curl -s http://localhost:11434/api/tags
echo.

echo ========================================
echo OPTIMIZACION COMPLETADA
echo ========================================
echo.
echo Presiona cualquier tecla para salir...
pause >nul
