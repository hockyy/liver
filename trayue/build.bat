@echo off

:: Name of your Python script
set SCRIPT_NAME=trayue.py

:: Check if PyInstaller is installed
pyinstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller is not installed.
)

:: Run PyInstaller with optimized settings
pyinstaller --onefile --windowed --optimize=2 "%SCRIPT_NAME%"

:: Check if the build was successful
if %errorlevel% equ 0 (
    echo Build successful. Executable can be found in the 'dist' directory.
) else (
    echo Build failed. Please check the output for errors.
)

pause