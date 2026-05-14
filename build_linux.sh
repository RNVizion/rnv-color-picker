#!/usr/bin/env bash
# ============================================================
# build_linux.sh - Build standalone Linux executable via PyInstaller
#
# Usage:  ./build_linux.sh
#         (or: bash build_linux.sh)
#
# Steps:
#   1. Verify Python is on PATH
#   2. Install/upgrade PyInstaller if needed
#   3. Clean previous build artifacts (calls clean_python_cache.sh)
#   4. Run PyInstaller against RNV_Color_Picker.spec
#   5. Report output location
#
# Output:  dist/RNV-Color-Picker  (executable binary, no .exe extension)
#
# Notes:
#   - First-time use: chmod +x build_linux.sh
#   - Requires Python 3.13+ on PATH (`python3` or `python`)
#   - Requires PyQt6 system dependencies; on Debian/Ubuntu:
#       sudo apt install libxcb-cursor0 libxkbcommon-x11-0
# ============================================================

set -e   # Exit immediately on any command failure
set -u   # Error on unset variables

# Pick whichever Python interpreter is available (prefer python3 on Linux)
if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    echo
    echo "ERROR: Neither python3 nor python is on PATH. Install Python 3.13+ and try again."
    echo
    exit 1
fi

echo
echo "=== RNV Color Picker - build ==="
echo

# --- 1. Verify Python is available ---
echo "[1/4] Checking for Python..."
PYTHON_VERSION="$("$PYTHON" --version 2>&1)"
echo "       Found: $PYTHON_VERSION"

# --- 2. Ensure PyInstaller is installed ---
echo
echo "[2/4] Checking for PyInstaller..."
if ! "$PYTHON" -m pip show pyinstaller >/dev/null 2>&1; then
    echo "       PyInstaller not found. Installing..."
    if ! "$PYTHON" -m pip install --upgrade "pyinstaller>=6.0"; then
        echo
        echo "ERROR: Failed to install PyInstaller."
        echo "       Try: $PYTHON -m pip install --user --upgrade 'pyinstaller>=6.0'"
        echo
        exit 1
    fi
else
    PYINSTALLER_VERSION="$("$PYTHON" -m pip show pyinstaller | grep '^Version:' | awk '{print $2}')"
    echo "       Found: PyInstaller $PYINSTALLER_VERSION"
fi

# --- 3. Clean previous build artifacts ---
echo
echo "[3/4] Cleaning previous build artifacts..."
if [ -f clean_python_cache.sh ]; then
    bash clean_python_cache.sh >/dev/null
else
    rm -rf build dist
fi

# --- 4. Build the executable ---
echo
echo "[4/4] Building executable from RNV_Color_Picker.spec..."
echo "       This may take 1-3 minutes depending on system speed."
echo
if ! "$PYTHON" -m PyInstaller RNV_Color_Picker.spec --noconfirm; then
    echo
    echo "ERROR: PyInstaller build failed. See output above."
    echo
    exit 1
fi

# --- Verify output ---
echo
OUTPUT_BIN="dist/RNV-Color-Picker"
if [ -f "$OUTPUT_BIN" ]; then
    # Ensure the binary is executable (PyInstaller usually sets this, but be defensive)
    chmod +x "$OUTPUT_BIN"
    OUTPUT_SIZE=$(stat -c%s "$OUTPUT_BIN" 2>/dev/null || stat -f%z "$OUTPUT_BIN" 2>/dev/null || echo "?")
    OUTPUT_ABS="$(cd "$(dirname "$OUTPUT_BIN")" && pwd)/$(basename "$OUTPUT_BIN")"
    echo "=== Build complete ==="
    echo "Output:  $OUTPUT_ABS"
    echo "Size:    $OUTPUT_SIZE bytes"
    echo
    echo "Run with:  ./$OUTPUT_BIN"
else
    echo "WARNING: Build reported success but $OUTPUT_BIN was not found."
    echo "Check the dist/ directory for the actual output."
    exit 1
fi

echo
