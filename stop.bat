@echo off
title Stopping Temple AI...
echo Stopping all servers...
taskkill /FI "WINDOWTITLE eq FastAPI Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Laravel Frontend*" /F >nul 2>&1
taskkill /IM "uvicorn.exe" /F >nul 2>&1
taskkill /IM "php.exe" /F >nul 2>&1
echo All servers stopped.
pause
