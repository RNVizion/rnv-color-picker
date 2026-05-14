# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for RNV Color Picker.

Build a standalone executable:

    # Install PyInstaller (not in requirements; install ad-hoc):
    pip install pyinstaller>=6.0

    # Build (single-file, windowed, with bundled resources):
    pyinstaller RNV_Color_Picker.spec

The output appears in `dist/RNV-Color-Picker.exe` (Windows) or
`dist/RNV-Color-Picker` (macOS/Linux).

Note on resource paths: the application reads `resources/` via paths
derived from `__file__` in `utils/config.py`. PyInstaller bundles
extract to `sys._MEIPASS` at runtime. The current path resolution may
need a small patch in `config.py` to detect the frozen state:

    import sys
    if getattr(sys, 'frozen', False):
        BASE_DIR = sys._MEIPASS
    else:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

This patch is left as a follow-up — uncomment the lines below if you
hit "resource not found" errors after building.
"""

from pathlib import Path

# Project root — the directory containing this spec file
HERE = Path('.').resolve()

# ---------------------------------------------------------------------
# Data files to bundle alongside the executable
# ---------------------------------------------------------------------
# Each tuple is (source_path_on_disk, destination_inside_bundle).
# At runtime, files appear under sys._MEIPASS/resources/...
datas = [
    ('resources/fonts',             'resources/fonts'),
    ('resources/icons',             'resources/icons'),
    ('resources/button_images',     'resources/button_images'),
    ('resources/background_images', 'resources/background_images'),
]


# ---------------------------------------------------------------------
# Hidden imports — modules PyInstaller can't auto-detect
# ---------------------------------------------------------------------
# scikit-learn imports several Cython extensions dynamically that
# PyInstaller's static analyzer misses. List them explicitly so the
# bundled .exe doesn't crash with ImportError when k-means runs.
hiddenimports = [
    'sklearn.utils._cython_blas',
    'sklearn.neighbors._typedefs',
    'sklearn.neighbors._quad_tree',
    'sklearn.tree._utils',
    'sklearn.utils._weight_vector',
]


# ---------------------------------------------------------------------
# Analysis — dependency graph for the application
# ---------------------------------------------------------------------
a = Analysis(
    ['RNV_Color_Picker.py'],
    pathex=[str(HERE)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude developer-only packages to keep the bundle small
        'pytest',
        'hypothesis',
        'coverage',
        # Exclude unused matplotlib/IPython if accidentally imported
        'matplotlib',
        'IPython',
        'jupyter',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)


# ---------------------------------------------------------------------
# Single-file executable
# ---------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RNV-Color-Picker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                    # Compress with UPX if available (smaller .exe)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                # Windowed app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/icon.png',
)
