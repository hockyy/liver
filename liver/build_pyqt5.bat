@echo off
echo ========================================
echo Building Subtitle Transcriber PRO (PyQt5)
echo ========================================

:: Name of your Python script
set SCRIPT_NAME=liver.py

:: Name of your icon file (should be in .ico format)
set ICON_FILE=liver.ico

:: Application name
set APP_NAME=SubtitleTranscriberPRO

:: Check if PyInstaller is installed
pyinstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller is not installed.
    echo Installing PyInstaller...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo Failed to install PyInstaller.
        exit /b 1
    )
)

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

:: Check if the icon file exists
if not exist "%ICON_FILE%" (
    echo [WARNING] Icon file not found: %ICON_FILE%
    echo Building without icon...
    set ICON_ARG=
) else (
    set ICON_ARG=--icon="%ICON_FILE%"
)

echo.
echo Cleaning previous build...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "%APP_NAME%.spec" del "%APP_NAME%.spec"

echo.
echo Building executable with PyQt5...

:: Run PyInstaller with PyQt5-specific settings
pyinstaller --name "%APP_NAME%" ^
            --onefile ^
            --windowed ^
            --optimize=2 ^
            %ICON_ARG% ^
            --hidden-import=PyQt5 ^
            --hidden-import=PyQt5.QtCore ^
            --hidden-import=PyQt5.QtGui ^
            --hidden-import=PyQt5.QtWidgets ^
            --collect-all PyQt5 ^
            --noupx ^
            "%SCRIPT_NAME%"

:: Check if the build was successful
if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo [SUCCESS] Build completed successfully!
    echo ========================================
    echo.
    echo Executable location: dist\%APP_NAME%.exe
    echo.
    
    :: Optional: Copy to a more accessible location
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

