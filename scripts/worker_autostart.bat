@echo off
REM =====================================================================
REM Worker Autostart - Synapse Council v2.2
REM Coloca este .bat en la carpeta de inicio de Windows del Worker:
REM   shell:startup  (Win+R -> shell:startup)
REM O ejecutalo manualmente al conectar por RDP.
REM =====================================================================

REM --- Solicitar elevacion UAC si no es administrador ---
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [UAC] Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

title Synapse Worker - Autostart
echo [Synapse Worker] Iniciando servicios...

REM --- Ollama (ya deberia estar como servicio, pero por si acaso) ---
echo [1/3] Verificando Ollama...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if %ERRORLEVEL% NEQ 0 (
    echo  -> Iniciando Ollama...
    start /B "" "C:\Users\maked\AppData\Local\Programs\Ollama\ollama.exe" serve
) else (
    echo  -> Ollama ya esta corriendo
)

REM --- LM Studio ---
echo [2/3] Verificando LM Studio...
tasklist /FI "IMAGENAME eq LM Studio.exe" 2>NUL | find /I "LM Studio.exe" >NUL
if %ERRORLEVEL% NEQ 0 (
    echo  -> Iniciando LM Studio en puerto 1235...
    start "" "C:\Program Files\LM Studio\LM Studio.exe"
) else (
    echo  -> LM Studio ya esta corriendo
)

REM --- Jan ---
echo [3/3] Verificando Jan...
tasklist /FI "IMAGENAME eq jan.exe" 2>NUL | find /I "jan.exe" >NUL
if %ERRORLEVEL% NEQ 0 (
    echo  -> Iniciando Jan en puerto 1337...
    start "" "C:\Users\maked\AppData\Local\Programs\jan\jan.exe"
) else (
    echo  -> Jan ya esta corriendo
)

REM --- Port forwarding: mantener accesible LM Studio desde la red ---
echo [4/4] Verificando port forwarding...
netsh interface portproxy show v4tov4 | find "1234" >NUL
if %ERRORLEVEL% NEQ 0 (
    netsh interface portproxy add v4tov4 listenport=1234 listenaddress=0.0.0.0 connectport=1234 connectaddress=127.0.0.1
    echo  -> Port forwarding 0.0.0.0:1234 -> 127.0.0.1:1234 creado
) else (
    echo  -> Port forwarding OK
)

echo.
echo [Synapse Worker] Todos los servicios iniciados.
echo  - Ollama :11434
echo  - LM Studio :1234
echo  - Jan :1337
echo.
echo Para verificar: http://localhost:11434
echo.
