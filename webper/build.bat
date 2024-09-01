@echo off

:: Name of your Python script
set SCRIPT_NAME=webper.py

:: Name of your icon file (should be in .ico format)
set ICON_FILE=webper.ico

:: Check if PyInstaller is installed
pyinstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller is not installed.
    exit /b 1
)

:: Check if the icon file exists
if not exist "%ICON_FILE%" (
    echo Icon file not found: %ICON_FILE%
    exit /b 1
)

:: Run PyInstaller with optimized settings and icon
pyinstaller --onefile --windowed --optimize=2 --icon="%ICON_FILE%" "%SCRIPT_NAME%"

:: Check if the build was successful
if %errorlevel% equ 0 (
    echo Build successful. Executable can be found in the 'dist' directory.
) else (
    echo Build failed. Please check the output for errors.
)

pause