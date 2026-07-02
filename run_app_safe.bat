@echo off
chcp 65001 >nul
title Tunnel Pump Control V5.7.25

pushd "%~dp0"

set VENV_DIR=%CD%\.venv
set PYTHON_EXE=%VENV_DIR%\Scripts\python.exe
set PIP_EXE=%VENV_DIR%\Scripts\pip.exe

echo.
echo ============================================================
echo  Tunnel Pump Control V5.7.25 - Startup
echo ============================================================
echo.

echo [Info] Current directory: %CD%

if not exist "%PYTHON_EXE%" (
    echo [Info] Virtual environment not found, creating...
    python -m venv .venv

    if %errorlevel% neq 0 (
        echo [Error] Failed to create virtual environment!
        pause
        popd
        exit /b 1
    )

    if exist requirements.txt (
        echo [Info] Installing dependencies from requirements.txt...
        "%PIP_EXE%" install --upgrade pip -q
        "%PIP_EXE%" install -r requirements.txt

        if %errorlevel% neq 0 (
            echo [Error] Failed to install dependencies!
            pause
            popd
            exit /b 1
        )
    )
) else (
    echo [Info] Virtual environment already exists, skipping dependency installation.
)

echo [Info] Checking virtual environment Python version...
"%PYTHON_EXE%" --version

echo [Info] Verifying cefpython3 installation...
"%PYTHON_EXE%" -c "import cefpython3; print('cefpython3 version:', cefpython3.__version__)"

if %errorlevel% neq 0 (
    echo [Error] cefpython3 module not installed!
    pause
    popd
    exit /b 1
)

echo.
echo [OK] All dependencies verified, starting application...
echo.

"%PYTHON_EXE%" "%CD%\src\main.py"

pause
popd