# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the CROPPS Demo GUI.

Build with:   pyinstaller cropps-demo.spec

Produces  dist/CROPPS-Demo/CROPPS-Demo.exe  (one-folder build).

The editable data folders `assets/` and `platform-tools/` are NOT embedded in
the bundle; they are copied next to the .exe by build_exe.py so users can edit
templates/images and so writable output (saves/, shared-images/,
assets/captured_data/) lands in plain folders. src/apppath.base_dir() resolves
all data paths to the folder that contains the .exe when frozen.
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = []

# Camera stack + unit handling — dynamically loaded, needs full collection.
for pkg in ("instrumental", "nicelib", "pint"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# assets/ is imported as a Python package (assets.burn / assets.injection) even
# though it has no __init__.py — force these submodules in explicitly.
hiddenimports += [
    "assets.burn",
    "assets.injection",
    "psycopg2",
    "serial",
    "serial.tools.list_ports",
    "watchdog.observers",
    "watchdog.observers.polling",
    "matplotlib.backends.backend_tkagg",
]
hiddenimports += collect_submodules("instrumental")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["oct2py", "octave_kernel"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CROPPS-Demo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CROPPS-Demo",
)
