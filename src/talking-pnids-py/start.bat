@echo off
REM Script to start both frontend and backend servers on Windows

echo Starting Talking P&IDs Application...
echo.

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Start backend
echo Starting backend server...
cd "%SCRIPT_DIR%backend"

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies if needed
if not exist "venv\.deps_installed" (
    echo Installing backend dependencies...
    pip install -r requirements.txt
    type nul > venv\.deps_installed
)

REM Start backend in background
start "Backend Server" cmd /c "python main.py"
echo Backend started
echo.

REM Wait a bit for backend to start
timeout /t 2 /nobreak >nul

REM Start frontend
echo Starting frontend server...
cd "%SCRIPT_DIR%frontend"

REM Check if node_modules exists
if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install
)

REM Start frontend in background
start "Frontend Server" cmd /c "npm run dev"
echo Frontend started
echo.

echo ========================================
echo Both servers are running!
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo ========================================
echo.
echo Close the command windows to stop the servers
pause
