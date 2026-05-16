@echo off
echo ========================================
echo   SynapseCode Control Center v2.7
echo ========================================
echo.
echo Iniciando servidor local en http://localhost:8080
echo.
cd /d "%~dp0frontend\control-center"
start "Synapse Control Center" cmd /k "python -m http.server 8080"
timeout /t 2 >nul
start "" "http://localhost:8080"
echo Control Center abierto en http://localhost:8080
echo.
echo Cierra esta ventana para detener el servidor.
pause
