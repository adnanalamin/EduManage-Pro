@echo off
REM ====================================================================
REM EduManage Pro - Windows Desktop Packaging Automation Script
REM Builds standalone EduManagePro.exe folder distribution
REM ====================================================================

echo ===================================================
echo   EduManage Pro - Building Windows Desktop Package
echo ===================================================

REM Check Python environment
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    pause
    exit /b 1
)

REM Activate virtual environment if present
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Install dependencies
echo Installing/Updating dependencies from requirements.txt...
pip install -r requirements.txt

REM Run unit test suite before compiling
echo Running security and unit test suite...
pytest tests/ -v
if %errorlevel% neq 0 (
    echo [WARNING] Some tests failed. Proceeding with caution...
)

REM Clean past build artifacts
echo Cleaning previous build outputs...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Run PyInstaller packaging
echo Packaging EduManage Pro with PyInstaller...
pyinstaller --clean EduManagePro.spec

if %errorlevel% equ 0 (
    echo ===================================================
    echo   BUILD SUCCESSFUL!
    echo   Standalone executable created at:
    echo   dist\EduManagePro\EduManagePro.exe
    echo ===================================================
) else (
    echo [ERROR] PyInstaller packaging encountered an issue.
)

pause
