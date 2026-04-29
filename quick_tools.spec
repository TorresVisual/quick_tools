# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['quick_tools.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\Moritz\\AppData\\Local\\Programs\\Python\\Python311\\tcl\\tcl8.6', '_tcl_data'), ('C:\\Users\\Moritz\\AppData\\Local\\Programs\\Python\\Python311\\tcl\\tk8.6', '_tk_data')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='quick_tools',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['quick_tools.ico'],
)
