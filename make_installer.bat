@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo School Bell - Professional Installer Builder
echo ==================================================
echo.

:: 1. Build the application directory
echo [1/2] Bundling application with PyInstaller...
python build_windows.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo BUILD FAILED! Please check the errors above.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Creating the Setup Installer...

:: Try to find Inno Setup compiler
set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "!ISCC!" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if exist "!ISCC!" (
    "!ISCC!" installer.iss
    if %ERRORLEVEL% neq 0 (
        echo.
        echo INSTALLER COMPILATION FAILED!
        pause
        exit /b %ERRORLEVEL%
    )
    echo.
    echo ==================================================
    echo SUCCESS! 
    echo Your installer is ready: Output\SchoolBell_Setup.exe
    echo ==================================================
) else (
    echo.
    echo WARNING: Inno Setup (ISCC.exe) not found in standard paths.
    echo Please open 'installer.iss' manually in Inno Setup and click 'Compile'.
)

echo.
pause
