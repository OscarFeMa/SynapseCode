@echo off
chcp 65001 >nul
title Instalador de Modelos - Synapse Council
color 0A
cls

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║           🤖 INSTALADOR DE MODELOS OLLAMA                   ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

:: Verificar Ollama
ollama --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ Ollama no está instalado
    echo    Descarga desde: https://ollama.ai
    pause
    exit /b 1
)

echo ✅ Ollama detectado
echo.

:: Menú de selección
echo Selecciona los modelos a instalar:
echo.
echo [1] Configuración recomendada (4 modelos, ~15GB)
echo     • llama3:8b    - Filósofo Racional (Meta)
echo     • mistral:7b   - Pragmatista Crítico (Mistral AI)
echo     • qwen2.5:3b   - Analista Sistémico (Alibaba)
echo     • deepseek-r1:7b - Escéptico Metodológico (DeepSeek)
echo.
echo [2] Configuración ligera (2 modelos, ~8GB)
echo     • llama3:8b
     • qwen2.5:3b
echo.
echo [3] Modelo individual

echo [4] Salir
echo.

set /p choice="Tu elección (1-4): "

if "%choice%"=="1" goto :recommended
if "%choice%"=="2" goto :lightweight
if "%choice%"=="3" goto :individual
if "%choice%"=="4" goto :exit
goto :invalid

:recommended
echo.
echo 📦 Instalando configuración recomendada...
echo Esto descargará ~15GB y puede tomar 30-60 minutos
echo.
pause
echo.

echo [1/4] Descargando llama3:8b...
ollama pull llama3:8b
echo.

echo [2/4] Descargando mistral:7b...
ollama pull mistral:7b
echo.

echo [3/4] Descargando qwen2.5:3b...
ollama pull qwen2.5:3b
echo.

echo [4/4] Descargando deepseek-r1:7b...
ollama pull deepseek-r1:7b
echo.

goto :complete

:lightweight
echo.
echo 📦 Instalando configuración ligera...
echo Esto descargará ~8GB
echo.
pause
echo.

echo [1/2] Descargando llama3:8b...
ollama pull llama3:8b
echo.

echo [2/2] Descargando qwen2.5:3b...
ollama pull qwen2.5:3b
echo.

goto :complete

:individual
echo.
echo Modelos disponibles:
echo   A - llama3:8b    (~4.7GB) - Buen equilibrio calidad/velocidad
echo   B - mistral:7b   (~4.1GB) - Excelente para razonamiento
echo   C - qwen2.5:3b  (~1.9GB) - Rápido y eficiente
echo   D - deepseek-r1:7b (~4.0GB) - Especializado en razonamiento
echo   E - gemma:7b     (~5.0GB) - Modelo de Google
echo   F - phi3:3.8b    (~2.3GB) - Microsoft, muy capaz
echo.

set /p model_choice="Selecciona (A-F): "

if /I "%model_choice%"=="A" set MODEL=llama3:8b
if /I "%model_choice%"=="B" set MODEL=mistral:7b
if /I "%model_choice%"=="C" set MODEL=qwen2.5:3b
if /I "%model_choice%"=="D" set MODEL=deepseek-r1:7b
if /I "%model_choice%"=="E" set MODEL=gemma:7b
if /I "%model_choice%"=="F" set MODEL=phi3:3.8b

if not defined MODEL (
    echo ❌ Opción inválida
    goto :individual
)

echo.
echo 📦 Descargando %MODEL%...
ollama pull %MODEL%
echo.

goto :complete

:invalid
echo ❌ Opción inválida
pause
exit /b 1

:complete
echo ╔════════════════════════════════════════════════════════════╗
echo ║               ✅ INSTALACIÓN COMPLETADA                      ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo Modelos instalados:
ollama list
echo.
echo 🚀 El sistema está listo para debates
echo 💡 Inicia el servidor: start_synapse.bat
pause
exit /b 0

:exit
echo.
echo 👋 Saliendo sin instalar modelos
echo 💡 Puedes instalar manualmente con: ollama pull [modelo]
pause
exit /b 0
