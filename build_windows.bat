@echo off
REM ============================================================
REM build_windows.bat - Build standalone Windows executable via PyInstaller
REM
REM Usage:  build_windows.bat
REM
REM Steps:
REM   1. Verify Python is on PATH
REM   2. Install/upgrade PyInstaller if needed
REM   3. Clean previous build artifacts (calls clean_python_cache.bat)
REM   4. Run PyInstaller against RNV_Color_Picker.spec
REM   5. Report output location
REM
REM Output:  dist\RNV-Color-Picker.exe
REM ============================================================

setlocal

echo.
echo === RNV Color Picker - build ===
echo.

REM --- 1. Verify Python is available ---
echo [1/4] Checking for Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python is not on PATH. Install Python 3.13+ and try again.
    echo.
    exit /b 1
)
for /f "delims=" %%v in ('python --version 2^>^&1') do echo        Found: %%v

REM --- 2. Ensure PyInstaller is installed ---
echo.
echo [2/4] Checking for PyInstaller...
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo        PyInstaller not found. Installing...
    python -m pip install --upgrade "pyinstaller>=6.0"
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to install PyInstaller.
        echo.
        exit /b 1
    )
) else (
    for /f "tokens=2" %%v in ('python -m pip show pyinstaller ^| findstr /b "Version:"') do echo        Found: PyInstaller %%v
)

REM --- 3. Clean previous build artifacts ---
echo.
echo [3/4] Cleaning previous build artifacts...
if exist clean_python_cache.bat (
    call clean_python_cache.bat >nul
) else (
    if exist build rd /s /q build
    if exist dist  rd /s /q dist
)

REM --- 4. Build the executable ---
echo.
echo [4/4] Building executable from RNV_Color_Picker.spec...
echo        This may take 1-3 minutes depending on system speed.
echo.
python -m PyInstaller RNV_Color_Picker.spec --noconfirm
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed. See output above.
    echo.
    exit /b 1
)

REM --- Verify output ---
echo.
if exist "dist\RNV-Color-Picker.exe" (
    for %%f in ("dist\RNV-Color-Picker.exe") do (
        echo === Build complete ===
        echo Output:  %%~ff
        echo Size:    %%~zf bytes
        echo.
        echo Run with:  dist\RNV-Color-Picker.exe
    )
) else (
    echo WARNING: Build reported success but dist\RNV-Color-Picker.exe was not found.
    echo Check the dist\ directory for the actual output.
    exit /b 1
)

echo.

endlocal
