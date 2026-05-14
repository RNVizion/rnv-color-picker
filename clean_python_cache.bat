@echo off
REM ============================================================
REM clean_python_cache.bat - Remove all Python, test, and build artifacts
REM
REM Usage:  clean_python_cache.bat
REM
REM Removes:
REM   - __pycache__ directories (recursive)
REM   - *.pyc / *.pyo files (recursive)
REM   - .pytest_cache, .mypy_cache, .ruff_cache, .hypothesis
REM   - .coverage, .coverage.*, htmlcov, coverage_report.txt
REM   - build, dist, *.egg-info
REM   - PyInstaller staging output
REM ============================================================

setlocal enabledelayedexpansion

echo.
echo === RNV Color Picker - clean ===
echo.

REM --- 1. Python bytecode caches (recursive) ---
echo [1/5] Removing __pycache__ directories...
for /d /r %%d in (__pycache__) do (
    if exist "%%d" rd /s /q "%%d" 2>nul
)

REM --- 2. Compiled bytecode files (recursive) ---
echo [2/5] Removing *.pyc and *.pyo files...
del /s /q *.pyc 2>nul >nul
del /s /q *.pyo 2>nul >nul

REM --- 3. Test and coverage caches ---
echo [3/5] Removing test/coverage caches...
if exist ".pytest_cache"   rd /s /q ".pytest_cache"
if exist ".hypothesis"     rd /s /q ".hypothesis"
if exist "htmlcov"         rd /s /q "htmlcov"
if exist ".coverage"       del /q ".coverage"
if exist ".coverage.unittest" del /q ".coverage.unittest"
if exist ".coverage.pytest"   del /q ".coverage.pytest"
if exist "coverage.xml"    del /q "coverage.xml"
if exist "coverage_report.txt" del /q "coverage_report.txt"

REM --- 4. Type checker / linter caches ---
echo [4/5] Removing type-checker and linter caches...
if exist ".mypy_cache"     rd /s /q ".mypy_cache"
if exist ".ruff_cache"     rd /s /q ".ruff_cache"
if exist ".pyre"           rd /s /q ".pyre"
if exist ".pytype"         rd /s /q ".pytype"

REM --- 5. Build / packaging artifacts ---
echo [5/5] Removing build and packaging artifacts...
if exist "build"           rd /s /q "build"
if exist "dist"            rd /s /q "dist"
if exist "build_pyinstaller" rd /s /q "build_pyinstaller"
for /d %%d in (*.egg-info) do (
    if exist "%%d" rd /s /q "%%d"
)

echo.
echo === Cleanup complete ===
echo.

endlocal
