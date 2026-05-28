@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

:: ==========================================
::  Reconciliation Tool v2.0 - Epic Pace Mode
:: ==========================================

:: ---- PERFORMANCE ENVIRONMENT VARIABLES ----
:: Prevent NumPy/Pandas thread oversubscription (thread thrashing on Windows)
set OMP_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
set MKL_NUM_THREADS=1
set VECLIB_MAXIMUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
set PYTHONDONTWRITEBYTECODE=1

:: ---- VALIDATE ENVIRONMENT ----
if not exist venv (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

:: ---- CHECK FOR ALREADY RUNNING INSTANCE ----
echo Checking for existing server instance...
set "SERVER_RUNNING=0"
for /f "tokens=*" %%a in ('wmic process where "CommandLine like '%%uvicorn%%backend.main%%'" get ProcessId 2^>nul ^| findstr /r "[0-9]"') do (
    set "SERVER_RUNNING=1"
    set "EXISTING_PID=%%a"
)

if "%SERVER_RUNNING%"=="1" (
    echo.
    echo ==========================================
    echo  SERVER ALREADY RUNNING
    echo ==========================================
    echo.
    echo Existing PID: %EXISTING_PID%
    echo URL: http://localhost:8000
    echo.
    echo To stop: taskkill /f /im python.exe
    echo.
    pause
    exit /b 0
)

:: ---- CREATE LOGS DIRECTORY ----
if not exist data\logs mkdir data\logs

:: ---- DISPLAY BANNER ----
echo ==========================================
echo  Reconciliation Tool v2.0 - Epic Pace Mode
echo ==========================================
echo.
echo Performance optimizations active:
echo   - NumPy/Pandas single-threaded (prevents thread thrashing)
echo   - High process priority
echo   - Increased concurrency: 500
echo   - Connection backlog: 4096
echo.
echo Starting server at http://localhost:8000
echo Health check: http://localhost:8000/health
echo Press Ctrl+C to stop
echo.

:: ---- AUTO-RESTART WRAPPER ----
:RESTART_LOOP

:: Start the server with epic-pace parameters
venv\Scripts\python -m uvicorn backend.main:app ^
    --host 0.0.0.0 ^
    --port 8000 ^
    --workers 1 ^
    --timeout-keep-alive 75 ^
    --limit-concurrency 500 ^
    --backlog 4096 ^
    --lifespan on ^
    --no-access-log

set "EXIT_CODE=%errorlevel%"

echo.
echo Server exited with code %EXIT_CODE% at %date% %time%

:: Exit code 0 = graceful shutdown, don't restart
:: Exit code 3 = intentional restart
if %EXIT_CODE% equ 0 (
    echo Graceful shutdown detected. Exiting.
    goto :END
)

:: Any other exit code = unexpected crash, auto-restart
echo ==========================================
echo  AUTO-RESTARTING SERVER
echo ==========================================
echo Restarting in 3 seconds...
timeout /t 3 /nobreak >nul
echo.
goto :RESTART_LOOP

:END
echo.
echo Server stopped. Press any key to exit.
pause >nul

endlocal