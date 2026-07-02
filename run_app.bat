@echo off
chcp 65001 >nul
title Tunnel Pump Control V5.7.25

cd /d "%~dp0"

set VENV_DIR=%~dp0.venv
set PYTHON_EXE=%VENV_DIR%\Scripts\python.exe
set PIP_EXE=%VENV_DIR%\Scripts\pip.exe

echo.
echo ============================================================
echo  Tunnel Pump Control V5.7.25 - Startup
echo ============================================================
echo.

set BASE_PYTHON=python

python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [Error] Python not found! Please install Python 3.10-3.11 64-bit.
        pause
        exit /b 1
    )
    set BASE_PYTHON=py
)

for /f "tokens=2" %%v in ('%BASE_PYTHON% --version 2^>^&1') do set PY_VER=%%v
for /f "tokens=1-2 delims=." %%a in ("%PY_VER%") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)

echo [Info] Current Python version: %PY_VER%

if %PY_MAJOR% geq 3 if %PY_MINOR% geq 12 (
    echo [Warning] Python %PY_VER% is NOT compatible with cefpython3!
    echo [Info] Trying to use Python 3.11...

    py -3.11 --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [Error] Python 3.11 not found!
        pause
        exit /b 1
    )

    set BASE_PYTHON=py -3.11
)

if not exist "%PYTHON_EXE%" (
    echo [Info] Virtual environment not found, creating...
    %BASE_PYTHON% -m venv .venv

    if %errorlevel% neq 0 (
        echo [Error] Failed to create virtual environment!
        pause
        exit /b 1
    )

    echo [OK] Virtual environment created successfully

    echo [Info] Activating virtual environment...
    call "%VENV_DIR%\Scripts\activate.bat"

    echo [Info] Installing dependencies from requirements.txt...
    if exist "requirements.txt" (
        "%PIP_EXE%" install --upgrade pip -q
        "%PIP_EXE%" install -r requirements.txt

        if %errorlevel% neq 0 (
            echo [Error] Failed to install dependencies from requirements.txt
            pause
            exit /b 1
        )
    ) else (
        echo [Warning] requirements.txt not found, skipping dependency installation.
    )
) else (
    echo [Info] Virtual environment already exists, skipping dependency installation.
    call "%VENV_DIR%\Scripts\activate.bat"
)

echo [Info] Checking virtual environment Python version...
"%PYTHON_EXE%" --version

echo [Info] Verifying cefpython3 installation...
"%PYTHON_EXE%" -c "import cefpython3; print('cefpython3 version:', cefpython3.__version__)"

if %errorlevel% neq 0 (
    echo [Error] cefpython3 module not installed!
    echo Please check requirements.txt or reinstall the virtual environment.
    pause
    exit /b 1
)

echo.
echo [OK] All dependencies verified, starting application...
echo.

"%PYTHON_EXE%" src\main.py

pause
