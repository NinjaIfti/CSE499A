@echo off
echo Starting Lecture Extraction System...
echo.

REM Activate virtual environment
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo Virtual environment activated
) else (
    echo WARNING: Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then run: venv\Scripts\activate
    echo Then run: pip install -r requirements.txt
    pause
    exit /b
)

REM Check if required packages are installed
venv\Scripts\python.exe -c "import streamlit" 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: Required packages not installed!
    echo Please run: pip install -r requirements.txt
    pause
    exit /b
)

REM Run Streamlit app
echo.
echo Launching Streamlit app...
echo Press Ctrl+C to stop the server
echo.
streamlit run app.py

pause
