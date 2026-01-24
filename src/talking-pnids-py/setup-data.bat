@echo off
REM Script to copy data files from JS project to Python project

set SCRIPT_DIR=%~dp0
set JS_DATA_DIR=%SCRIPT_DIR%..\talking-pnids-js\data
set PY_DATA_DIR=%SCRIPT_DIR%data

echo Setting up data directory...

REM Create data directories
if not exist "%PY_DATA_DIR%\pdfs" mkdir "%PY_DATA_DIR%\pdfs"
if not exist "%PY_DATA_DIR%\jsons" mkdir "%PY_DATA_DIR%\jsons"
if not exist "%PY_DATA_DIR%\mds" mkdir "%PY_DATA_DIR%\mds"

REM Copy files if source exists
if exist "%JS_DATA_DIR%" (
    echo Copying PDFs...
    xcopy "%JS_DATA_DIR%\pdfs\*" "%PY_DATA_DIR%\pdfs\" /Y /Q
    
    echo Copying JSONs...
    xcopy "%JS_DATA_DIR%\jsons\*" "%PY_DATA_DIR%\jsons\" /Y /Q
    
    echo Copying Markdown files...
    xcopy "%JS_DATA_DIR%\mds\*" "%PY_DATA_DIR%\mds\" /Y /Q
    
    echo Data files copied successfully!
) else (
    echo Error: JS project data directory not found at %JS_DATA_DIR%
    echo Please ensure the talking-pnids-js project exists in the parent directory
)

pause
