@echo off
setlocal enabledelayedexpansion
:: ============================================================
:: Doc to Markdown — Windows Installer Build Script
:: by Darksquare  |  https://darksquare.dev
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
::   installer\Output\DocToMarkdown_Setup_1.2.0.exe
:: ============================================================

set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"

echo.
echo ============================================================
echo   Doc to Markdown — Installer Build
echo   Darksquare
echo ============================================================
echo.

:: ── Step 1: Verify Python ──────────────────────────────────
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python not found in PATH.
    echo   Install Python 3.10+ from https://python.org
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
echo   Python %PYVER% found.

:: ── Step 2: Verify PyInstaller ─────────────────────────────
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

:: ── Step 3: Stage vendored binaries (Tesseract) ────────────
echo.
echo [3/5] Staging bundled engines (Tesseract)...
python installer\stage_vendor.py
if errorlevel 1 (
    echo   ERROR: Failed to stage vendored binaries.
    echo   Ensure Tesseract is installed first: python setup.py
    exit /b 1
)

:: ── Step 4: Run PyInstaller ────────────────────────────────
echo.
echo [4/5] Building application with PyInstaller...
echo   This may take several minutes on first run.
echo.

:: Clean previous build artifacts
if exist "dist\DocToMarkdown" rd /s /q "dist\DocToMarkdown"
if exist "build\DocToMarkdown" rd /s /q "build\DocToMarkdown"

python -m PyInstaller installer\doctomarkdown.spec --noconfirm
if errorlevel 1 (
    echo.
    echo   ERROR: PyInstaller build failed.
    echo   Check the output above for missing modules or import errors.
    echo   Common fix: pip install -r requirements.txt
    exit /b 1
)

:: Verify the executable was created
if not exist "dist\DocToMarkdown\DocToMarkdown.exe" (
    echo   ERROR: Expected dist\DocToMarkdown\DocToMarkdown.exe not found.
    exit /b 1
)
echo   Build complete: dist\DocToMarkdown\DocToMarkdown.exe

:: ── Step 5: Run Inno Setup Compiler ───────────────────────
echo.
echo [5/5] Building installer with Inno Setup...

:: Try common ISCC locations
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
) else (
    :: Try PATH
    where iscc >nul 2>&1
    if not errorlevel 1 (
        set "ISCC=iscc"
    )
)

if "!ISCC!"=="" (
    echo.
    echo   WARNING: Inno Setup compiler (ISCC.exe) not found.
    echo   Install Inno Setup 6 from: https://jrsoftware.org/isinfo.php
    echo.
    echo   PyInstaller build succeeded. You can compile the installer
    echo   manually by opening installer\doctomarkdown.iss in Inno Setup.
    exit /b 0
)

echo   Using: !ISCC!
"!ISCC!" installer\doctomarkdown.iss
if errorlevel 1 (
    echo.
    echo   ERROR: Inno Setup compilation failed.
    echo   Open installer\doctomarkdown.iss in Inno Setup IDE to debug.
    exit /b 1
)

echo.
echo ============================================================
echo   BUILD COMPLETE
echo.
echo   Installer: installer\Output\DocToMarkdown_Setup_1.2.0.exe
echo ============================================================
echo.

exit /b 0
