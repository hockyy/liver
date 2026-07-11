@echo off
echo ========================================
echo Building Subtitle Transcriber PRO (PyQt5)
echo ========================================

set APP_NAME=SubtitleTranscriberPRO
set SPEC_FILE=%APP_NAME%.spec

:: Check if PyQt5 is installed
python -c "import PyQt5" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PyQt5 is not installed.
    echo Installing PyQt5...
    pip install PyQt5
    if %errorlevel% neq 0 (
        echo Failed to install PyQt5.
        exit /b 1
    )
)

:: Check if PyInstaller is installed
python -m PyInstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller is not installed.
    echo Installing PyInstaller...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo Failed to install PyInstaller.
        exit /b 1
    )
)

:: PyInstaller still imports pkg_resources via altgraph; setuptools 82+ removed it
python -c "import pkg_resources" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] pkg_resources missing ^(setuptools 82+^). Pinning setuptools^<81...
    pip install "setuptools<81"
    if %errorlevel% neq 0 (
        echo Failed to install compatible setuptools.
        exit /b 1
    )
)

if not exist "%SPEC_FILE%" (
    echo [ERROR] Spec file not found: %SPEC_FILE%
    exit /b 1
)

echo.
echo Cleaning previous build...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

echo.
echo Building executable from %SPEC_FILE%...

python -m PyInstaller "%SPEC_FILE%" --noconfirm

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo [SUCCESS] Build completed successfully!
    echo ========================================
    echo.
    echo Executable location: dist\%APP_NAME%.exe
    echo.

    if not exist "release" mkdir release
    copy "dist\%APP_NAME%.exe" "release\" >nul 2>&1
    if %errorlevel% equ 0 (
        echo Also copied to: release\%APP_NAME%.exe
    )
) else (
    echo.
    echo ========================================
    echo [ERROR] Build failed!
    echo ========================================
    echo Please check the output above for errors.
)

echo.
pause
