@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo  Reconciliation Tool v2.0 - Service Installer
echo ==========================================
echo.
echo This will install the Reconciliation Tool as a Windows Service.
echo Requires Administrator privileges.
echo.

cd /d "%~dp0"

:: ---- VALIDATE ENVIRONMENT ----
if not exist venv (
    echo ERROR: Virtual environment not found!
    pause
    exit /b 1
)

:: ---- CHECK ADMIN PRIVILEGES ----
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Administrator privileges required!
    echo Please run this batch file as Administrator.
    pause
    exit /b 1
)

:: ---- INSTALL NSSM IF NOT PRESENT ----
if not exist "tools\nssm.exe" (
    echo [INFO] Downloading NSSM (Non-Sucking Service Manager)...
    if not exist tools mkdir tools

    powershell -Command "& {
        $url = 'https://nssm.cc/release/nssm-2.24.zip';
        $output = 'tools\nssm.zip';
        try {
            Invoke-WebRequest -Uri $url -OutFile $output -UseBasicParsing;
            Expand-Archive -Path $output -DestinationPath 'tools\' -Force;
            Copy-Item 'tools\nssm-2.24\win64\nssm.exe' 'tools\nssm.exe' -Force;
            Remove-Item 'tools\nssm.zip' -Force;
            Remove-Item 'tools\nssm-2.24' -Recurse -Force;
            Write-Host 'NSSM installed successfully';
        } catch {
            Write-Host 'Failed to download NSSM. Please install manually from https://nssm.cc';
            exit 1;
        }
    }"

    if not exist "tools\nssm.exe" (
        echo ERROR: Could not install NSSM.
        pause
        exit /b 1
    )
)

:: ---- SERVICE CONFIGURATION ----
set "SERVICE_NAME=ReconciliationTool"
set "APP_DIR=%~dp0"
set "PYTHON=%APP_DIR%venv\Scripts\python.exe"
set "LOG_DIR=%APP_DIR%data\logs"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: ---- STOP AND REMOVE EXISTING SERVICE ----
echo [INFO] Stopping existing service (if any)...
sc stop %SERVICE_NAME% >nul 2>&1
timeout /t 2 /nobreak >nul
sc delete %SERVICE_NAME% >nul 2>&1
timeout /t 1 /nobreak >nul

:: ---- INSTALL NEW SERVICE ----
echo [INFO] Installing service: %SERVICE_NAME%

:: Base install
tools\nssm.exe install %SERVICE_NAME% "%PYTHON%"
tools\nssm.exe set %SERVICE_NAME% Application "%PYTHON%"

:: Epic-pace command with optimizations
:: --workers 1 is REQUIRED to prevent SQLite/DuckDB multiprocess conflicts
tools\nssm.exe set %SERVICE_NAME% Arguments "-m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1 --timeout-keep-alive 75 --limit-concurrency 500 --backlog 4096 --lifespan on --no-access-log"

tools\nssm.exe set %SERVICE_NAME% AppDirectory "%APP_DIR%"
tools\nssm.exe set %SERVICE_NAME% DisplayName "Reconciliation Tool Server v2.0"
tools\nssm.exe set %SERVICE_NAME% Description "Enterprise Reconciliation Tool - Epic Pace FastAPI Backend"
tools\nssm.exe set %SERVICE_NAME% Start SERVICE_AUTO_START

:: ---- LOGGING ----
tools\nssm.exe set %SERVICE_NAME% AppStdout "%LOG_DIR%\service_out.log"
tools\nssm.exe set %SERVICE_NAME% AppStderr "%LOG_DIR%\service_err.log"
tools\nssm.exe set %SERVICE_NAME% AppRotateFiles 1
tools\nssm.exe set %SERVICE_NAME% AppRotateOnline 1
tools\nssm.exe set %SERVICE_NAME% AppRotateBytes 10485760

:: ---- PERFORMANCE ENVIRONMENT VARIABLES ----
:: Prevent NumPy/Pandas thread oversubscription (thread thrashing on Windows)
tools\nssm.exe set %SERVICE_NAME% AppEnvironmentExtra "OMP_NUM_THREADS=1;OPENBLAS_NUM_THREADS=1;MKL_NUM_THREADS=1;VECLIB_MAXIMUM_THREADS=1;NUMEXPR_NUM_THREADS=1;PYTHONDONTWRITEBYTECODE=1"

:: ---- RESTART ON FAILURE ----
tools\nssm.exe set %SERVICE_NAME% AppRestartDelay 3000
tools\nssm.exe set %SERVICE_NAME% AppThrottle 5000

:: ---- PROCESS PRIORITY ----
:: 3 = High priority (ensures smooth processing during heavy loads)
tools\nssm.exe set %SERVICE_NAME% AppPriority 3

:: ---- START SERVICE ----
echo [INFO] Starting service...
net start %SERVICE_NAME%

if %errorlevel% == 0 (
    echo.
    echo ==========================================
    echo  SERVICE INSTALLED SUCCESSFULLY
    echo ==========================================
    echo.
    echo Service Name: %SERVICE_NAME%
    echo URL: http://localhost:8000
    echo Health: http://localhost:8000/health
    echo Logs: %LOG_DIR%
    echo.
    echo Performance optimizations active:
    echo   - NumPy/Pandas single-threaded (prevents thread thrashing)
    echo   - High process priority
    echo   - Increased concurrency: 500
    echo   - Connection backlog: 4096
    echo.
    echo To manage:
    echo   - Stop:   net stop %SERVICE_NAME%
    echo   - Start:  net start %SERVICE_NAME%
    echo   - Remove: sc delete %SERVICE_NAME%
    echo.
) else (
    echo [ERROR] Failed to start service. Check logs: %LOG_DIR%
    echo [INFO] Try running: tools\nssm.exe status %SERVICE_NAME%
)

pause
endlocal