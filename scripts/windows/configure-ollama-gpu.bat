@echo off
REM ========================================
REM CONFIGURACION DE OLLAMA PARA GPU
REM Synapse Council - GPU Optimization
REM ========================================

echo.
echo ========================================
echo CONFIGURACION DE OLLAMA PARA GPU
echo ========================================
echo.

echo [1/5] Verificando instalacion de Ollama...
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Ollama no esta instalado o no esta en PATH.
    echo Por favor, instala Ollama desde https://ollama.com
    pause
    exit /b 1
)
echo Ollama instalado.
echo.

echo [2/5] Verificando GPU NVIDIA...
nvidia-smi >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] No se detecta GPU NVIDIA o nvidia-smi no esta instalado.
    echo Por favor, instala los drivers de NVIDIA CUDA.
    pause
    exit /b 1
)
echo GPU NVIDIA detectada.
echo.

echo --- Informacion de GPU ---
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
echo.

echo [3/5] Configurando Ollama para usar GPU...
setx OLLAMA_NUM_GPU 999
setx OLLAMA_GPU_OVERHEAD 0
setx OLLAMA_LOAD_TIMEOUT 5m
setx OLLAMA_KEEP_ALIVE -1
setx OLLAMA_MAX_QUEUE 4
setx OLLAMA_MAX_LOADED_MODELS 2
setx OLLAMA_FLASH_ATTENTION 1
setx OLLAMA_KV_CACHE_TYPE f16
setx CUDA_VISIBLE_DEVICES 0
echo Variables de entorno configuradas.
echo.

echo [4/5] Descargando modelos optimizados para GPU...
echo.
echo Descargando llama3:8b (requiere ~4.6GB VRAM)...
ollama pull llama3:8b
echo.

echo Descargando qwen2.5:7b (requiere ~4.2GB VRAM)...
ollama pull qwen2.5:7b
echo.

echo Descargando mistral:7b (requiere ~4.1GB VRAM)...
ollama pull mistral:7b
echo.

echo [5/5] Verificando modelos descargados...
echo.
echo --- Modelos disponibles ---
ollama list
echo.

echo --- Probando modelo con GPU ---
ollama run llama3:8b "Hola, responde en una sola palabra: GPU"
echo.

echo ========================================
echo CONFIGURACION COMPLETADA
echo ========================================
echo.
echo Modelos optimizados para GPU descargados:
echo - llama3:8b
echo - qwen2.5:7b
echo - mistral:7b
echo.
echo Para usar estos modelos en Synapse Master:
echo 1. Actualiza round_controller.py con los nombres de los modelos
echo 2. Reinicia el Master
echo 3. Ejecuta una sesion de prueba
echo.
echo Presiona cualquier tecla para salir...
pause >nul
