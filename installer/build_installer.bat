@echo off
setlocal enabledelayedexpansion
:: ============================================================
:: Markwell - Windows Installer Build Script
:: by Darksquare  ^|  https://darksquare.dev
::
:: Prerequisites:
::   1. Python 3.10+ with project dependencies installed
::   2. PyInstaller:  pip install pyinstaller
::   3. Inno Setup 6: https://jrsoftware.org/isinfo.php
::
:: Usage:
::   installer\build_installer.bat
::
:: Output:
::   installer\Output\Markwell_Setup_1.0.0.exe
:: ============================================================

set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"

echo.
echo ============================================================
echo   Markwell - Installer Build
echo   Darksquare
echo ============================================================
echo.

:: --- Step 1: Verify Python ---
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python not found in PATH.
    echo   Install Python 3.10+ from https://python.org
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
echo   Python %PYVER% found.

:: --- Step 2: Verify PyInstaller ---
echo.
echo [2/5] Checking PyInstaller...
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo   PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo   ERROR: Failed to install PyInstaller.
        exit /b 1
    )
)
for /f %%v in ('python -m PyInstaller --version 2^>^&1') do set "PIVER=%%v"
echo   PyInstaller %PIVER% found.

:: --- Step 3: Stage vendored binaries (Tesseract) ---
echo.
echo [3/5] Staging bundled engines (Tesseract)...
python installer\stage_vendor.py
if errorlevel 1 (
    echo   ERROR: Failed to stage vendored binaries.
    echo   Ensure Tesseract is installed first: python setup.py
    exit /b 1
)

:: --- Step 4: Run PyInstaller ---
echo.
echo [4/5] Building application with PyInstaller...
echo   This may take several minutes on first run.
echo.

:: Clean previous build artifacts
if exist "dist\Markwell" rd /s /q "dist\Markwell"
if exist "build\Markwell" rd /s /q "build\Markwell"

python -m PyInstaller installer\markwell.spec --noconfirm
if errorlevel 1 (
    echo.
    echo   ERROR: PyInstaller build failed.
    echo   Check the output above for missing modules or import errors.
    echo   Common fix: pip install -r requirements.txt
    exit /b 1
)

:: Verify the executable was created
if not exist "dist\Markwell\Markwell.exe" (
    echo   ERROR: Expected dist\Markwell\Markwell.exe not found.
    exit /b 1
)
echo   Build complete: dist\Markwell\Markwell.exe

:: Generate the styled HTML Quick Start Guide for the installer's post-install action
echo.
echo   Generating Quick Start Guide (Guide.html)...
python installer\make_guide_html.py
if errorlevel 1 (
    echo   WARNING: Guide.html generation failed - installer will still build.
)

:: --- Step 5: Run Inno Setup Compiler ---
:: NOTE: ISCC detection uses single-line ifs and goto labels (no parenthesized
:: blocks) because the "(x86)" path and parentheses break cmd block parsing.
echo.
echo [5/5] Building installer with Inno Setup...

set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if not defined ISCC where iscc >nul 2>&1 && set "ISCC=iscc"

if not defined ISCC goto no_iscc

echo   Using: !ISCC!
"!ISCC!" installer\markwell.iss
if errorlevel 1 goto iscc_failed

echo.
echo ============================================================
echo   BUILD COMPLETE
echo.
echo   Installer: installer\Output\Markwell_Setup_1.0.0.exe
echo ============================================================
echo.
exit /b 0

:no_iscc
echo.
echo   WARNING: Inno Setup compiler ISCC.exe was not found.
echo   Install Inno Setup 6 from: https://jrsoftware.org/isinfo.php
echo.
echo   PyInstaller build succeeded. Compile the installer manually by
echo   opening installer\markwell.iss in Inno Setup.
exit /b 0

:iscc_failed
echo.
echo   ERROR: Inno Setup compilation failed.
echo   Open installer\markwell.iss in Inno Setup IDE to debug.
exit /b 1
