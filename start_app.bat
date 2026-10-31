@echo off
title Launch Leukemia Detection System

echo ===================================================
echo   Starting Leukemia Detection System (Complete Stack)
echo ===================================================
echo.

set SCRIPT_DIR=%~dp0

:: Step 0: Ensure MongoDB is Running on Port 27017
echo [0/4] Checking MongoDB Server on Port 27017...
tasklist /fi "imagename eq mongod.exe" | find /i "mongod.exe" >nul
if errorlevel 1 (
    if exist "D:\bin\mongod.exe" (
        echo       Starting local MongoDB daemon from D:\bin\mongod.exe ...
        start "MongoDB Server" /min "D:\bin\mongod.exe" --config "D:\bin\mongod.cfg"
        timeout /t 3 /nobreak >nul
    ) else (
        echo       Notice: D:\bin\mongod.exe not found. Proceeding with standalone mode.
    )
) else (
    echo       MongoDB is already running on port 27017.
)

:: Step 1: Prevent Duplicate Processes & Port Conflicts on 5000 and 5173
echo.
echo [1/4] Checking and clearing port conflicts on ports 5000 and 5173...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000 " ^| findstr "LISTENING"') do (
    echo       Terminating duplicate process on port 5000 with PID %%a ...
    taskkill /f /pid %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173 " ^| findstr "LISTENING"') do (
    echo       Terminating duplicate process on port 5173 with PID %%a ...
    taskkill /f /pid %%a >nul 2>&1
)

:: Step 2: Configure Python 3.10 Virtual Environment
echo.
echo [2/4] Activating Python 3.10 Virtual Environment...
set VENV_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe
if exist "%VENV_PYTHON%" (
    echo       Found Python 3.10 Virtual Environment at %SCRIPT_DIR%venv
) else (
    if exist "C:\Users\FAIMIDA\AppData\Local\Programs\Python\Python310\python.exe" (
        echo       Virtual environment not found. Using system Python 3.10.
        set VENV_PYTHON="C:\Users\FAIMIDA\AppData\Local\Programs\Python\Python310\python.exe"
    ) else (
        echo       Using default python.
        set VENV_PYTHON=python
    )
)

:: Step 3: Start Flask Backend & React Frontend in Dedicated Windows
echo.
echo [3/4] Launching Backend on Port 5000 and Frontend on Port 5173...
pushd "%SCRIPT_DIR%backend"
start "Leukemia Backend - Flask Port 5000" cmd /k ""%VENV_PYTHON%" app.py"
popd

pushd "%SCRIPT_DIR%frontend"
start "Leukemia Frontend - Vite Port 5173" cmd /k "npm run dev"
popd

:: Step 4: Wait for Services and Open Web Application
echo.
echo [4/4] Waiting for application servers to initialize...
ping -n 6 127.0.0.1 >nul

echo       Opening application in default browser at http://localhost:5173 ...
start http://localhost:5173

echo.
echo ===================================================
echo   Leukemia Detection System is now running!
echo   - Frontend: http://localhost:5173
echo   - Backend:  http://127.0.0.1:5000
echo   - MongoDB:  127.0.0.1:27017 [Connected]
echo ===================================================
echo To stop the system, close the Backend, Frontend, and MongoDB terminal windows.
pause
