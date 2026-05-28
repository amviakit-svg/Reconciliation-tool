@echo off
echo ============================================
echo   Reconciliation Tool - Deploy Builder
echo ============================================
echo.

REM Navigate to script directory
cd /d "%~dp0"

REM Check Python availability
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Python found:
python --version
echo.

REM Run the deployment builder
echo Starting build process...
echo This may take several minutes on first run.
echo.
python deploy\build_standalone.py %*

echo.
echo ============================================
echo Build process completed.
echo Check the dist\ folder for output.
echo ============================================
pause