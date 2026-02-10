@echo off
echo ========================================
echo Lecture Extraction System - Setup
echo ========================================
echo.

REM Check Python installation (try both python and py)
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python is not installed or not in PATH!
        echo Please install Python 3.8+ from https://www.python.org/
        pause
        exit /b
    )
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python
)

echo Python found!
%PYTHON_CMD% --version
echo.

REM Create virtual environment
echo Creating virtual environment...
%PYTHON_CMD% -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment!
    pause
    exit /b
)
echo Virtual environment created successfully!
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Upgrade pip
echo Upgrading pip...
%PYTHON_CMD% -m pip install --upgrade pip
echo.

REM Install requirements
echo Installing dependencies (this may take a while)...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install some dependencies!
    echo Please check the error messages above.
    pause
    exit /b
)

echo.
echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo To run the application:
echo   1. Run: venv\Scripts\activate
echo   2. Run: streamlit run app.py
echo.
echo Or simply double-click run.bat
echo.
pause
