@echo off
title Launch Leukemia Detection System

echo ===================================================
echo   Starting Leukemia Detection System (Backend & Frontend)
echo ===================================================
echo.

set SCRIPT_DIR=%~dp0

echo 1. Starting Flask Backend Server (Port 5000)...
start "Leukemia Backend (Flask)" cmd /k "cd /d "%SCRIPT_DIR%backend" && python app.py"

echo 2. Starting React/Vite Frontend Server (Port 5173)...
start "Leukemia Frontend (Vite)" cmd /k "cd /d "%SCRIPT_DIR%frontend" && npm run dev"

echo.
echo 3. Waiting 5 seconds for servers to initialize...
timeout /t 5 /nobreak >nul

echo.
echo 4. Opening Frontend in default browser (http://localhost:5173)...
start http://localhost:5173

echo.
echo ===================================================
echo   Both services are now running in separate terminals!
echo   To stop the application, close the terminal windows.
echo ===================================================
pause
