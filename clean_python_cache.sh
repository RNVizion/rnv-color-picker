#!/usr/bin/env bash
# ============================================================
# clean_python_cache.sh - Remove all Python, test, and build artifacts
#
# Usage:  ./clean_python_cache.sh
#         (or: bash clean_python_cache.sh)
#
# Removes:
#   - __pycache__ directories (recursive)
#   - *.pyc / *.pyo files (recursive)
#   - .pytest_cache, .mypy_cache, .ruff_cache, .hypothesis
#   - .coverage, .coverage.*, htmlcov, coverage_report.txt
#   - build, dist, *.egg-info
#   - PyInstaller staging output
# ============================================================

set -u  # Error on unset variables (but allow non-zero exits — many
        # rm targets won't exist on a clean tree, that's fine)

echo
echo "=== RNV Color Picker - clean ==="
echo

# --- 1. Python bytecode caches (recursive) ---
echo "[1/5] Removing __pycache__ directories..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# --- 2. Compiled bytecode files (recursive) ---
echo "[2/5] Removing *.pyc and *.pyo files..."
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# --- 3. Test and coverage caches ---
echo "[3/5] Removing test/coverage caches..."
rm -rf .pytest_cache .hypothesis htmlcov
rm -f .coverage .coverage.unittest .coverage.pytest coverage.xml coverage_report.txt

# --- 4. Type checker / linter caches ---
echo "[4/5] Removing type-checker and linter caches..."
rm -rf .mypy_cache .ruff_cache .pyre .pytype

# --- 5. Build / packaging artifacts ---
echo "[5/5] Removing build and packaging artifacts..."
rm -rf build dist build_pyinstaller
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

echo
echo "=== Cleanup complete ==="
echo
