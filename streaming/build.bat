@echo off

:: Name of your Python script
set SCRIPT_NAME=streamer.py

:: Name of your output executable
set EXE_NAME=StreamingToolsLauncher

:: Check if PyInstaller is installed
pyinstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller is not installed.
    echo Installing PyInstaller...
    pip install pyinstaller
)

:: Run PyInstaller with optimized settings
echo Building %EXE_NAME%...
pyinstaller --onefile --windowed --optimize=2 --name="%EXE_NAME%" "%SCRIPT_NAME%"

:: Check if the build was successful
if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Build successful!
    echo Executable: dist\%EXE_NAME%.exe
    echo ========================================
) else (
    echo.
    echo Build failed. Please check the output for errors.
)

pause

