@echo off
title Synapse Web Agent - Session Setup
cd /d D:\Synapse_2026-05-26

echo ============================================
echo Synapse Web Agent - Configuracion de Sesiones
echo ============================================
echo.
echo Este asistente abrira Chromium para que
echo inicies sesion en los sitios de IA.
echo.
echo Al terminar de logearte, vuelve a esta
echo ventana y presiona ENTER para continuar.
echo.

python scripts\setup_web_sessions.py

echo.
pause
