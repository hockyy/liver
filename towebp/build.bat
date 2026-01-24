@echo off
echo ========================================
echo  MOV to WebP Converter - Build Script
echo ========================================
echo.

:: Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
    echo.
)

:: Clean previous builds
echo Cleaning previous builds...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "*.spec" del /q *.spec
echo.

:: Build the executable
echo Building executable...
pyinstaller --onefile --windowed --name "MOVtoWebP" --icon=NONE gui.py

echo.
if exist "dist\MOVtoWebP.exe" (
    echo ========================================
    echo  Build successful!
    echo  Output: dist\MOVtoWebP.exe
    echo ========================================
    echo.
    echo NOTE: FFmpeg must be installed on the
    echo target machine for the app to work.
    echo.
) else (
    echo ========================================
    echo  Build failed!
    echo ========================================
)

pause
