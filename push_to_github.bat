@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

title Subir a GitHub - Synapse Council
color 0B
cls

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║           🚀 SUBIR SYNAPSE COUNCIL A GITHUB                 ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

:: Verificar git
where git >nul 2>nul
if %errorLevel% neq 0 (
    echo ❌ Git no está instalado o no está en PATH
    echo    Descarga Git desde: https://git-scm.com/download/win
    pause
    exit /b 1
)

echo ✅ Git detectado

:: Verificar si es repo git
if not exist .git (
    echo ℹ️  Inicializando repositorio Git...
    git init
    echo ✅ Repositorio inicializado
) else (
    echo ✅ Repositorio Git ya existe
)
echo.

:: Configurar git si no está configurado
git config user.name >nul 2>&1 || (
    echo 📝 Configurando Git por primera vez...
    set /p gitname="Tu nombre para GitHub: "
    set /p gitemail="Tu email para GitHub: "
    git config user.name "!gitname!"
    git config user.email "!gitemail!"
    echo ✅ Git configurado
)
echo.

:: Agregar archivos
echo 📦 Agregando archivos al commit...
git add .
echo ✅ Archivos agregados
echo.

:: Verificar si hay cambios para commitear
git diff --cached --quiet
if %errorLevel% equ 0 (
    echo ℹ️  No hay cambios nuevos para subir
    goto :push
)

:: Hacer commit
echo 💾 Creando commit...
set commitmsg=Release v2.0 - %date% %time:~0,5%
git commit -m "!commitmsg!"
echo ✅ Commit creado: !commitmsg!
echo.

:push
:: Verificar remote
git remote -v >nul 2>&1
if %errorLevel% neq 0 (
    echo 🔗 Configurando remote de GitHub...
    echo.
    echo Para continuar necesitas:
    echo 1. Crear repositorio en: https://github.com/new
    echo 2. Copiar la URL (HTTPS o SSH)
    echo.
    set /p repo_url="URL del repositorio GitHub: "
    
    if "!repo_url!"=="" (
        echo ❌ URL no proporcionada
        pause
        exit /b 1
    )
    
    git remote add origin !repo_url!
    echo ✅ Remote configurado: !repo_url!
) else (
    echo ✅ Remote ya configurado
git remote -v
)
echo.

:: Push a GitHub
echo ☁️  Subiendo a GitHub...
echo    Esto puede tomar varios minutos la primera vez...
echo.

git push -u origin main 2>nul || git push -u origin master

if %errorLevel% equ 0 (
    echo.
    echo ╔════════════════════════════════════════════════════════════╗
    echo ║               ✅ ¡SUBIDA COMPLETADA!                          ║
    echo ╚════════════════════════════════════════════════════════════╝
    echo.
    for /f "tokens=*" %%a in ('git remote get-url origin') do echo URL: %%a
    echo.
    echo Tu código está ahora en GitHub!
) else (
    echo.
    echo ❌ Error al subir. Posibles causas:
    echo    • No tienes permisos en el repositorio
    echo    • Necesitas autenticarte con GitHub
    echo    • El repositorio no existe
    echo.
    echo Para autenticar con GitHub:
    echo    1. Instala GitHub CLI: winget install GitHub.cli
    echo    2. Ejecuta: gh auth login
    echo    3. Vuelve a ejecutar este script
)

echo.
pause
