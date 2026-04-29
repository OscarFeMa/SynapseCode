@echo off
REM Script de empaquetamiento para Windows usando PyInstaller
REM Este script crea ejecutables .exe para Master y Worker

echo ========================================
echo Pensamiento Coral - Empaquetamiento Windows
echo ========================================
echo.

REM Verificar que PyInstaller está instalado
python -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller no encontrado. Instalando...
    python -m pip install pyinstaller
)

REM Instalar dependencias
echo Instalando dependencias...
python -m pip install customtkinter

REM Crear directorio de salida
if not exist "dist" mkdir dist

REM Empaquetar Master
echo.
echo Empaquetando Master.py...
pyinstaller --onefile --windowed --name "PensamientoCoral_Master" --icon=NONE --add-data "src/config.py;." "src/Master.py"

if %errorlevel% neq 0 (
    echo ERROR: Falló el empaquetamiento de Master
    pause
    exit /b 1
)

REM Empaquetar Worker
echo.
echo Empaquetando Worker.py...
pyinstaller --onefile --name "PensamientoCoral_Worker" --icon=NONE --add-data "src/config.py;." "src/Worker.py"

if %errorlevel% neq 0 (
    echo ERROR: Falló el empaquetamiento de Worker
    pause
    exit /b 1
)

echo.
echo ========================================
echo Empaquetamiento completado exitosamente
echo ========================================
echo.
echo Los ejecutables se encuentran en la carpeta dist/
echo - PensamientoCoral_Master.exe
echo - PensamientoCoral_Worker.exe
echo.

pause
