@echo off
title Temple AI Crowd Management System
color 0A

echo ===============================================
echo   Temple AI Crowd Management System
echo   Starting Redis + Backend + Frontend...
echo ===============================================
echo.

REM ── Step 1: Start Redis ────────────────────────
echo [1/3] Starting Redis (port 6379)...
set REDIS_EXE=C:\Users\HP\AppData\Local\Microsoft\WinGet\Packages\taizod1024.redis-windows-fork_Microsoft.Winget.Source_8wekyb3d8bbwe\Redis-8.8.0-Windows-x64-msys2\redis-server.exe
start "Redis Server" /min "%REDIS_EXE%"
timeout /t 3 /nobreak >nul

REM ── Step 2: Start FastAPI Backend ─────────────
echo [2/3] Starting FastAPI Backend (port 8000)...
start "FastAPI Backend" cmd /k "cd /d C:\crowd_management_backend\backend && venv\Scripts\activate && venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 5 /nobreak >nul

REM ── Step 3: Start React Frontend ──────────────
echo [3/3] Starting React Frontend (port 3000)...
start "React Frontend" cmd /k "cd /d C:\crowd_management_backend\react-frontend && npm run dev"
timeout /t 3 /nobreak >nul

echo.
echo ===============================================
echo   All 3 services started!
echo.
echo   Redis            : localhost:6379
echo   FastAPI Backend  : http://127.0.0.1:8000
echo   API Docs (Swagger): http://127.0.0.1:8000/docs
echo   React Frontend   : http://localhost:3000
echo ===============================================
echo.
pause
